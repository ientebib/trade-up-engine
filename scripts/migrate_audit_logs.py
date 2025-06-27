#!/usr/bin/env python3
"""
Script to migrate audit logs from flat structure to date-based folders
Old: logs/financial_audit/financial_audit_20250627_0001.jsonl
New: logs/financial_audit/2025/06/27/audit_0001.jsonl
"""
import os
import shutil
from pathlib import Path
import re
from datetime import datetime

def migrate_audit_logs():
    """Migrate audit logs to new directory structure"""
    log_dir = Path("logs/financial_audit")
    
    if not log_dir.exists():
        print("❌ No audit log directory found")
        return
    
    # Find all old-style log files
    old_pattern = re.compile(r'financial_audit_(\d{8})_(\d{4})\.jsonl')
    migrated = 0
    errors = 0
    
    for log_file in log_dir.glob("financial_audit_*.jsonl"):
        match = old_pattern.match(log_file.name)
        if not match:
            print(f"⚠️  Skipping unrecognized file: {log_file.name}")
            continue
            
        date_str = match.group(1)
        file_index = match.group(2)
        
        try:
            # Parse date
            date = datetime.strptime(date_str, "%Y%m%d")
            
            # Create new directory structure
            new_dir = log_dir / f"{date.year:04d}/{date.month:02d}/{date.day:02d}"
            new_dir.mkdir(parents=True, exist_ok=True)
            
            # New filename
            new_file = new_dir / f"audit_{file_index}.jsonl"
            
            # Move file
            print(f"📁 Moving {log_file.name} → {new_file.relative_to(log_dir)}")
            shutil.move(str(log_file), str(new_file))
            migrated += 1
            
        except Exception as e:
            print(f"❌ Error migrating {log_file.name}: {e}")
            errors += 1
    
    print(f"\n✅ Migration complete!")
    print(f"   Files migrated: {migrated}")
    print(f"   Errors: {errors}")
    
    # Show new structure
    if migrated > 0:
        print("\n📂 New directory structure:")
        for year_dir in sorted(log_dir.iterdir()):
            if year_dir.is_dir() and year_dir.name.isdigit():
                print(f"   {year_dir.name}/")
                for month_dir in sorted(year_dir.iterdir()):
                    if month_dir.is_dir():
                        day_count = sum(1 for d in month_dir.iterdir() if d.is_dir())
                        print(f"      {month_dir.name}/ ({day_count} days)")

if __name__ == "__main__":
    print("🔄 Migrating audit logs to date-based folder structure...")
    migrate_audit_logs()