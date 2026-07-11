import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from musicsort.models.domain import OperationPreview, DuplicateGroup
from musicsort.core.config import DEFAULT_REPORTS_DIR
from musicsort.core.logger import get_operations_logger, get_errors_logger

class ReportGenerator:
    """
    Generates reports summarizing organization and duplicate checks.
    Outputs report.txt, duplicates.txt, and organization_history.json.
    """
    def __init__(self):
        self.op_logger = get_operations_logger()
        self.err_logger = get_errors_logger()

    def generate_execution_report(
        self,
        previews: List[OperationPreview],
        scan_root: Path,
        target_root: Path,
        conflict_mode: str,
        backup_id: Optional[str] = None
    ) -> Path:
        """
        Generates report.txt summarizing file movement results, and updates organization_history.json.
        """
        report_path = DEFAULT_REPORTS_DIR / "report.txt"
        history_path = DEFAULT_REPORTS_DIR / "organization_history.json"
        
        total_ops = len(previews)
        success_count = sum(1 for op in previews if op.status == "success")
        skipped_count = sum(1 for op in previews if op.status == "skipped")
        failed_count = sum(1 for op in previews if op.status == "failed")
        
        timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 1. Write report.txt
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("=" * 60 + "\n")
                f.write(f"MUSIC SORT - EXECUTION REPORT\n")
                f.write(f"Run Timestamp: {timestamp_str}\n")
                f.write("=" * 60 + "\n\n")
                
                f.write(f"DIRECTORIES:\n")
                f.write(f"- Source Library: {scan_root}\n")
                f.write(f"- Target Library: {target_root}\n")
                if backup_id:
                    f.write(f"- Backup Session ID: {backup_id}\n")
                f.write("\n")
                
                f.write(f"STATISTICS:\n")
                f.write(f"- Conflict Resolution Mode: {conflict_mode}\n")
                f.write(f"- Total Operations Previews: {total_ops}\n")
                f.write(f"- Successfully Moved/Renamed: {success_count}\n")
                f.write(f"- Skipped Moves: {skipped_count}\n")
                f.write(f"- Failed Moves: {failed_count}\n\n")
                
                f.write("=" * 60 + "\n")
                f.write("DETAILED OPERATIONS:\n")
                f.write("=" * 60 + "\n")
                
                if not previews:
                    f.write("No file rename or move operations performed.\n")
                else:
                    for op in previews:
                        f.write(f"[{op.status.upper()}] - {op.operation_type.upper()}\n")
                        f.write(f"  Source: {op.original_path}\n")
                        f.write(f"  Target: {op.target_path}\n")
                        if op.error_message:
                            f.write(f"  Reason: {op.error_message}\n")
                        f.write("-" * 40 + "\n")
                        
            self.op_logger.info(f"Execution report generated successfully at: {report_path}")
        except Exception as e:
            self.err_logger.error(f"Failed to generate execution report: {e}")

        # 2. Update organization_history.json
        try:
            history_data = []
            if history_path.exists():
                with open(history_path, "r", encoding="utf-8") as hf:
                    try:
                        history_data = json.load(hf)
                        if not isinstance(history_data, list):
                            history_data = []
                    except Exception:
                        pass
            
            # Append new run details
            run_entry = {
                "timestamp": timestamp_str,
                "source": str(scan_root),
                "target": str(target_root),
                "conflict_mode": conflict_mode,
                "backup_id": backup_id or "",
                "total_ops": total_ops,
                "success_count": success_count,
                "skipped_count": skipped_count,
                "failed_count": failed_count,
                "files": [
                    {
                        "song_id": op.song_id,
                        "original_path": str(op.original_path),
                        "target_path": str(op.target_path),
                        "operation_type": op.operation_type,
                        "status": op.status,
                        "error_message": op.error_message or ""
                    } for op in previews
                ]
            }
            history_data.append(run_entry)
            
            with open(history_path, "w", encoding="utf-8") as hf:
                json.dump(history_data, hf, indent=4, ensure_ascii=False)
                
            self.op_logger.info(f"History index updated successfully at: {history_path}")
        except Exception as e:
            self.err_logger.error(f"Failed to update organization history json: {e}")
            
        return report_path

    def generate_duplicates_report(self, groups: List[DuplicateGroup]) -> Path:
        """
        Generates duplicates.txt details for the found duplicates list.
        """
        report_path = DEFAULT_REPORTS_DIR / "duplicates.txt"
        
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("=" * 60 + "\n")
                f.write(f"MUSIC SORT - DUPLICATE SCAN REPORT\n")
                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")
                
                f.write(f"SUMMARY: Found {len(groups)} duplicate groups.\n\n")
                
                for idx, g in enumerate(groups):
                    f.write(f"Group #{idx+1} | Strategy: {g.criteria} | Confidence Score: {g.confidence}%\n")
                    f.write(f"Group ID: {g.id}\n")
                    f.write("-" * 40 + "\n")
                    
                    for song in g.files:
                        size_mb = song.size_bytes / (1024 * 1024)
                        f.write(f"- Path: {song.path}\n")
                        f.write(f"  Size: {size_mb:.2f} MB | Dur: {song.duration:.1f}s | Bitrate: {song.bitrate}kbps\n")
                        f.write(f"  Artist/Title: {song.artist} - {song.title}\n")
                        f.write(f"  Hash: {song.file_hash}\n")
                    f.write("\n" + "="*40 + "\n\n")
                    
            self.op_logger.info(f"Duplicates report generated at: {report_path}")
        except Exception as e:
            self.err_logger.error(f"Failed to generate duplicates report: {e}")
            
        return report_path
