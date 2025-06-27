# Financial Audit Logs

## Directory Structure

Audit logs are organized by date for easier management:

```
financial_audit/
├── 2025/
│   ├── 06/
│   │   ├── 26/
│   │   │   ├── audit_0001.jsonl
│   │   │   ├── audit_0002.jsonl
│   │   │   └── ...
│   │   └── 27/
│   │       ├── audit_0001.jsonl
│   │       └── ...
│   └── ...
└── README.md
```

## Log Rotation

- Each file has a maximum size of 100MB
- Each file has a maximum of 10,000 entries
- New files are created automatically when limits are reached

## Automatic Cleanup

- Logs older than 30 days are automatically deleted
- Cleanup runs daily at startup and every 24 hours

## Migration

To migrate old flat-structure logs to the new organized structure:

```bash
python scripts/migrate_audit_logs.py
```

This will move files from:
- `financial_audit_20250627_0001.jsonl` 
  
To:
- `2025/06/27/audit_0001.jsonl`