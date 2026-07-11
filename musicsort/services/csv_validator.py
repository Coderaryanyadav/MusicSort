import csv
from pathlib import Path
from typing import List, Dict, Set, Tuple
from musicsort.models.domain import Song, CSVRecord, ValidationIssue
from musicsort.core.config import ALLOWED_FOLDERS, DEFAULT_REPORTS_DIR
from musicsort.core.logger import get_validation_logger, get_errors_logger

class CSVValidator:
    """
    Parses and validates a CSV file for organizing music, checking against files on disk.
    Generates validation_report.txt and logs to validation.log.
    """
    def __init__(self):
        self.val_logger = get_validation_logger()
        self.err_logger = get_errors_logger()

    def validate_csv(self, csv_path: Path, scanned_songs: List[Song], scan_root: Path) -> Tuple[List[CSVRecord], List[ValidationIssue], Path]:
        """
        Validates CSV content and returns a tuple of:
        (Parsed records, validation issues, path to validation_report.txt)
        """
        self.val_logger.info(f"Starting validation for CSV: {csv_path}")
        
        records: List[CSVRecord] = []
        issues: List[ValidationIssue] = []
        
        # 1. Parse CSV
        raw_rows: List[Dict[str, str]] = []
        try:
            with open(csv_path, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                
                # Check for required headers
                headers = reader.fieldnames if reader.fieldnames else []
                normalized_headers = [h.strip().lower() for h in headers]
                
                required = ["filename", "new_filename", "folder"]
                missing_headers = [req for req in required if req not in normalized_headers]
                
                if missing_headers:
                    msg = f"CSV is missing required headers: {', '.join(missing_headers)}"
                    self.val_logger.error(msg)
                    issues.append(ValidationIssue(
                        type="invalid_headers",
                        message=msg,
                        severity="error",
                        details=f"Headers found: {headers}"
                    ))
                    # Can't parse further
                    return [], issues, self._write_report(csv_path, issues, scanned_songs, records)

                # Store mapping of original headers to normalize case
                header_map = {}
                for h in headers:
                    header_map[h.strip().lower()] = h

                for idx, row in enumerate(reader):
                    # Clean spacing
                    cleaned_row = {
                        "filename": row.get(header_map["filename"], "").strip(),
                        "new_filename": row.get(header_map["new_filename"], "").strip(),
                        "folder": row.get(header_map["folder"], "").strip()
                    }
                    raw_rows.append((idx + 2, cleaned_row)) # row index (1-based, plus header row)
        except Exception as e:
            msg = f"Failed to parse CSV: {e}"
            self.err_logger.error(msg)
            issues.append(ValidationIssue(type="parse_error", message=msg, severity="error"))
            return [], issues, self._write_report(csv_path, issues, scanned_songs, [])

        # Sets to trace duplicates and matching
        seen_rows: Set[Tuple[str, str, str]] = set()
        seen_filenames: Set[str] = set()
        seen_destinations: Set[Tuple[str, str]] = set() # (folder, new_filename)
        
        # Build lookup maps for scanned songs
        scanned_by_name: Dict[str, List[Song]] = {}
        scanned_by_rel_path: Dict[str, Song] = {}
        scanned_by_abs_path: Dict[str, Song] = {}
        
        for s in scanned_songs:
            scanned_by_name.setdefault(s.path.name.lower(), []).append(s)
            try:
                rel = s.path.relative_to(scan_root)
                scanned_by_rel_path[str(rel).lower()] = s
            except Exception:
                pass
            scanned_by_abs_path[str(s.path).lower()] = s

        matched_songs: Set[Path] = set()

        for line_num, r in raw_rows:
            # Check empty fields
            empty_fields = [k for k, v in r.items() if not v]
            if empty_fields:
                issues.append(ValidationIssue(
                    type="empty_field",
                    message=f"Row {line_num} has empty fields: {', '.join(empty_fields)}",
                    severity="error",
                    row_index=line_num,
                    details=str(r)
                ))
            
            # Record validation fields
            filename = r["filename"]
            new_filename = r["new_filename"]
            folder = r["folder"]
            
            # Clean record for addition if parse is successful
            record = CSVRecord(filename=filename, new_filename=new_filename, folder=folder)
            records.append(record)

            # Check duplicate rows (exact matches in CSV)
            row_key = (filename.lower(), new_filename.lower(), folder.lower())
            if row_key in seen_rows:
                issues.append(ValidationIssue(
                    type="duplicate_row",
                    message=f"Row {line_num} is an exact duplicate of a previous row in the CSV.",
                    severity="warning",
                    row_index=line_num,
                    details=f"Values: {filename}, {new_filename}, {folder}"
                ))
            seen_rows.add(row_key)

            # Check duplicate source filename mappings in CSV
            if filename.lower() in seen_filenames:
                issues.append(ValidationIssue(
                    type="duplicate_filename",
                    message=f"Row {line_num} maps the source file '{filename}' which is already mapped elsewhere in the CSV.",
                    severity="error",
                    row_index=line_num,
                    details=f"Source file: {filename}"
                ))
            seen_filenames.add(filename.lower())

            # Check duplicate destination names (two sources moving to the same target in the same folder)
            dest_key = (folder.lower(), new_filename.lower())
            if dest_key in seen_destinations:
                issues.append(ValidationIssue(
                    type="duplicate_destination",
                    message=f"Row {line_num} maps to destination '{new_filename}' in folder '{folder}', which is already targeted by another row.",
                    severity="error",
                    row_index=line_num,
                    details=f"Target: {folder}/{new_filename}"
                ))
            seen_destinations.add(dest_key)

            # Check folder validity
            if folder and folder not in ALLOWED_FOLDERS:
                issues.append(ValidationIssue(
                    type="invalid_folder",
                    message=f"Row {line_num} targets folder '{folder}', which is not in the allowed list.",
                    severity="error",
                    row_index=line_num,
                    details=f"Allowed folders: {', '.join(ALLOWED_FOLDERS)}"
                ))

            # Match CSV filename to disk file
            matched_song = None
            fn_lower = filename.lower()
            
            # Priority 1: Absolute path match
            if fn_lower in scanned_by_abs_path:
                matched_song = scanned_by_abs_path[fn_lower]
            # Priority 2: Relative path match
            elif fn_lower in scanned_by_rel_path:
                matched_song = scanned_by_rel_path[fn_lower]
            # Priority 3: Filename match
            elif fn_lower in scanned_by_name:
                songs_list = scanned_by_name[fn_lower]
                if len(songs_list) == 1:
                    matched_song = songs_list[0]
                elif len(songs_list) > 1:
                    # Ambiguous filename match
                    issues.append(ValidationIssue(
                        type="ambiguous_match",
                        message=f"Row {line_num} maps filename '{filename}', which matches multiple songs on disk.",
                        severity="error",
                        row_index=line_num,
                        details=f"Matches found: {[str(s.path) for s in songs_list]}"
                    ))

            if matched_song:
                matched_songs.add(matched_song.path)
                # Assign folder classification override from CSV
                if folder in ALLOWED_FOLDERS:
                    matched_song.folder_assignment = folder
            else:
                if filename:
                    issues.append(ValidationIssue(
                        type="missing_song",
                        message=f"Row {line_num}: Song '{filename}' listed in CSV is not found on disk.",
                        severity="error",
                        row_index=line_num,
                        details=f"Filename query: {filename}"
                    ))

        # Check for songs on disk not listed in CSV
        for song in scanned_songs:
            if song.path not in matched_songs:
                issues.append(ValidationIssue(
                    type="extra_file",
                    message=f"Song on disk '{song.path.name}' is not listed in the CSV.",
                    severity="warning",
                    details=f"Path: {song.path}"
                ))

        # Log summary of issues
        error_count = sum(1 for iss in issues if iss.severity == "error")
        warning_count = sum(1 for iss in issues if iss.severity == "warning")
        self.val_logger.info(f"Validation completed. Errors: {error_count}, Warnings: {warning_count}")

        # Write final validation report
        report_path = self._write_report(csv_path, issues, scanned_songs, records)
        return records, issues, report_path

    def _write_report(self, csv_path: Path, issues: List[ValidationIssue], scanned_songs: List[Song], records: List[CSVRecord]) -> Path:
        """Writes details to validation_report.txt in default reports directory."""
        report_path = DEFAULT_REPORTS_DIR / "validation_report.txt"
        
        error_count = sum(1 for iss in issues if iss.severity == "error")
        warning_count = sum(1 for iss in issues if iss.severity == "warning")
        
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("=" * 60 + "\n")
                f.write(f"MUSIC SORT - CSV VALIDATION REPORT\n")
                f.write(f"CSV File: {csv_path}\n")
                f.write("=" * 60 + "\n\n")
                
                f.write(f"SUMMARY:\n")
                f.write(f"- Total CSV Rows Parsed: {len(records)}\n")
                f.write(f"- Total Songs Scanned on Disk: {len(scanned_songs)}\n")
                f.write(f"- Validation Errors: {error_count}\n")
                f.write(f"- Validation Warnings: {warning_count}\n\n")
                
                if error_count == 0:
                    f.write("Status: VALIDATION SUCCESSFUL. App is ready to organize songs.\n\n")
                else:
                    f.write("Status: VALIDATION FAILED. Resolve errors before proceeding.\n\n")
                
                f.write("=" * 60 + "\n")
                f.write("DETAILED ISSUES:\n")
                f.write("=" * 60 + "\n")
                
                if not issues:
                    f.write("No issues detected!\n")
                else:
                    for iss in issues:
                        row_str = f"Row {iss.row_index} | " if iss.row_index else ""
                        f.write(f"[{iss.severity.upper()}] - {iss.type.upper()} - {row_str}{iss.message}\n")
                        if iss.details:
                            f.write(f"  Details: {iss.details}\n")
                        f.write("-" * 40 + "\n")
                        
            # Also log details to validation.log
            for iss in issues:
                log_msg = f"[{iss.severity.upper()}] {iss.type}: {iss.message}"
                if iss.row_index:
                    log_msg += f" (Row {iss.row_index})"
                if iss.severity == "error":
                    self.val_logger.error(log_msg)
                else:
                    self.val_logger.warning(log_msg)
                    
        except Exception as e:
            self.err_logger.error(f"Failed to write validation report: {e}")
            
        return report_path
