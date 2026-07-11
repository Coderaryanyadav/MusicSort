import os
import json
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Callable

from musicsort.models.domain import Song, OperationPreview
from musicsort.core.config import ALLOWED_FOLDERS, CHECKPOINT_FILE_NAME
from musicsort.core.logger import get_operations_logger, get_errors_logger

class MoveEngine:
    """
    Handles file rename and move operations, conflict resolution (Rename/Skip/Replace),
    checkpointing (to allow resuming after interruption), and progress/ETA reporting.
    """
    def __init__(self):
        self.op_logger = get_operations_logger()
        self.err_logger = get_errors_logger()

    def generate_previews(self, songs: List[Song], target_root: Path, csv_mappings: Optional[List[Dict[str, str]]] = None) -> List[OperationPreview]:
        """
        Generates preview operations indicating what rename/move operations will occur.
        """
        previews: List[OperationPreview] = []
        
        # Build mapping for CSV override
        csv_map: Dict[str, Tuple[str, str]] = {} # original_name_lower -> (new_name, folder)
        if csv_mappings:
            for m in csv_mappings:
                csv_map[m["filename"].lower()] = (m["new_filename"], m["folder"])

        for song in songs:
            orig_path = song.path
            
            # Determine new filename and target folder
            new_filename = orig_path.name
            target_folder = song.folder_assignment  # default is "Others" or what matched CSV
            
            # If CSV has mapped details, apply them
            fn_lower = orig_path.name.lower()
            if fn_lower in csv_map:
                csv_new_fn, csv_folder = csv_map[fn_lower]
                if csv_new_fn:
                    new_filename = csv_new_fn
                if csv_folder:
                    target_folder = csv_folder
            else:
                # If no CSV mapping, use metadata cleaned name
                # Make sure we preserve extension!
                ext = orig_path.suffix
                cleaned_base = song.title if song.title else orig_path.stem
                if song.artist and song.artist != "Unknown Artist":
                    cleaned_base = f"{song.artist} - {cleaned_base}"
                # Append extension if not already present
                if not cleaned_base.lower().endswith(ext.lower()):
                    new_filename = f"{cleaned_base}{ext}"
                else:
                    new_filename = cleaned_base

            # Enforce destination folder structure
            if target_folder not in ALLOWED_FOLDERS:
                target_folder = "Others"

            target_path = target_root / target_folder / new_filename
            
            # Determine operation type
            is_same_dir = orig_path.parent.resolve() == target_path.parent.resolve()
            is_same_name = orig_path.name == target_path.name
            
            if is_same_dir and is_same_name:
                # No actual movement needed
                continue
            elif is_same_dir:
                op_type = "rename"
            elif is_same_name:
                op_type = "move"
            else:
                op_type = "rename_and_move"

            previews.append(OperationPreview(
                original_path=orig_path,
                target_path=target_path,
                operation_type=op_type,
                status="pending"
            ))
            
        return previews

    def execute_operations(
        self,
        previews: List[OperationPreview],
        conflict_mode: str,  # "Rename", "Skip", "Replace"
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
        checkpoint_dir: Optional[Path] = None
    ) -> Tuple[int, int, List[OperationPreview]]:
        """
        Executes the list of move/rename operations.
        Returns: (success_count, failed_count, updated_previews)
        """
        total = len(previews)
        success_count = 0
        failed_count = 0
        
        # Load progress if checkpoint_dir and checkpoint file exist
        completed_paths: Dict[str, str] = {} # orig_path_str -> status
        checkpoint_file = None
        
        if checkpoint_dir:
            checkpoint_file = checkpoint_dir / CHECKPOINT_FILE_NAME
            if checkpoint_file.exists():
                try:
                    with open(checkpoint_file, "r", encoding="utf-8") as f:
                        completed_paths = json.load(f)
                    self.op_logger.info(f"Loaded resume checkpoint with {len(completed_paths)} processed files.")
                except Exception as e:
                    self.err_logger.error(f"Failed to load checkpoint file: {e}")

        self.op_logger.info(f"Executing {total} operations with conflict mode: {conflict_mode}")

        for idx, op in enumerate(previews):
            # Check for cancellation request
            if cancel_check and cancel_check():
                self.op_logger.info("Operation execution cancelled by user.")
                break

            orig_str = str(op.original_path)
            
            # Resume check
            if orig_str in completed_paths:
                status = completed_paths[orig_str]
                op.status = status
                if status == "success":
                    success_count += 1
                elif status in ["failed", "conflict"]:
                    failed_count += 1
                if progress_callback:
                    progress_callback(idx + 1, total, f"Skipping already processed file: {op.original_path.name}")
                continue

            # Ensure source file still exists
            if not op.original_path.exists():
                op.status = "failed"
                op.error_message = "Source file not found."
                failed_count += 1
                self.err_logger.error(f"Source file not found: {op.original_path}")
                self._update_checkpoint(checkpoint_file, orig_str, "failed", completed_paths)
                continue

            # Ensure target parent folder exists
            try:
                op.target_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                op.status = "failed"
                op.error_message = f"Failed to create target folder: {e}"
                failed_count += 1
                self.err_logger.error(f"Failed to create folder {op.target_path.parent}: {e}")
                self._update_checkpoint(checkpoint_file, orig_str, "failed", completed_paths)
                continue

            # Resolve conflict if target path exists
            final_target_path = op.target_path
            status_set = "success"
            
            if final_target_path.exists() and final_target_path.resolve() != op.original_path.resolve():
                if conflict_mode == "Skip":
                    op.status = "skipped"
                    op.error_message = "Destination file exists (skipped)."
                    self.op_logger.info(f"Skipping file due to conflict: {op.original_path.name}")
                    self._update_checkpoint(checkpoint_file, orig_str, "skipped", completed_paths)
                    continue
                    
                elif conflict_mode == "Rename":
                    # Generate a unique filename by adding suffixes
                    base = final_target_path.stem
                    ext = final_target_path.suffix
                    parent = final_target_path.parent
                    counter = 1
                    while final_target_path.exists():
                        final_target_path = parent / f"{base} - {counter}{ext}"
                        counter += 1
                    self.op_logger.info(f"Conflict: Renamed target to {final_target_path.name}")
                    op.target_path = final_target_path
                    
                elif conflict_mode == "Replace":
                    # We will replace/overwrite. Check if same file first
                    try:
                        self.op_logger.info(f"Conflict: Overwriting existing file: {final_target_path}")
                        # Remove destination file first to perform clean move
                        final_target_path.unlink()
                    except Exception as e:
                        op.status = "failed"
                        op.error_message = f"Conflict Replace failed: {e}"
                        failed_count += 1
                        self.err_logger.error(f"Failed to delete existing file for replacement: {final_target_path}. Error: {e}")
                        self._update_checkpoint(checkpoint_file, orig_str, "failed", completed_paths)
                        continue

            # Perform the move operation (which does both rename and move)
            try:
                # Update progress message
                if progress_callback:
                    progress_callback(idx + 1, total, f"Moving: {op.original_path.name} -> {op.target_path.name}")
                
                # Use shutil.move (never copy or symlink, as per requirements)
                shutil.move(str(op.original_path), str(final_target_path))
                op.status = "success"
                success_count += 1
                self.op_logger.info(f"Successfully moved: {op.original_path} -> {final_target_path}")
                self._update_checkpoint(checkpoint_file, orig_str, "success", completed_paths)
            except Exception as e:
                op.status = "failed"
                op.error_message = str(e)
                failed_count += 1
                self.err_logger.error(f"Failed to move {op.original_path} to {final_target_path}: {e}")
                self._update_checkpoint(checkpoint_file, orig_str, "failed", completed_paths)

        # Execution finished, clean up checkpoint if complete and successful
        if checkpoint_file and checkpoint_file.exists() and failed_count == 0:
            try:
                checkpoint_file.unlink()
                self.op_logger.info("Task completed successfully. Checkpoint file removed.")
            except Exception as e:
                self.err_logger.error(f"Failed to delete checkpoint file: {e}")
                
        return success_count, failed_count, previews

    def _update_checkpoint(self, checkpoint_file: Optional[Path], orig_str: str, status: str, completed_paths: Dict[str, str]):
        """Helper to write the current progress to the checkpoint file."""
        if not checkpoint_file:
            return
        completed_paths[orig_str] = status
        try:
            with open(checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(completed_paths, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.err_logger.error(f"Failed to write checkpoint update: {e}")
            
    def remove_checkpoint(self, checkpoint_dir: Path):
        """Manually removes checkpoint file if requested."""
        checkpoint_file = checkpoint_dir / CHECKPOINT_FILE_NAME
        if checkpoint_file.exists():
            try:
                checkpoint_file.unlink()
                self.op_logger.info("Checkpoint file deleted manually.")
            except Exception as e:
                self.err_logger.error(f"Failed to delete checkpoint file: {e}")
