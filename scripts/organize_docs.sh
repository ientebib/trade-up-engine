#!/usr/bin/env bash
# Script to reorganize Markdown documentation into structured docs/ directories
set -euo pipefail

BASE_DIR=$(dirname "$0")/..
cd "$BASE_DIR"

mkdir -p docs/architecture docs/audits docs/reports docs/setup docs/queries docs/reference docs/guides

# Move architecture docs
git mv SERVICE_LAYER_ARCHITECTURE.md docs/architecture/ || true
git mv DATA_ARCHITECTURE.md docs/architecture/ || true
git mv BUSINESS_CONTEXT.md docs/architecture/ || true

# Move audit docs
git mv API_RESPONSE_AUDIT.md docs/audits/ || true
git mv FRONTEND_API_AUDIT.md docs/audits/ || true
git mv HEALTH_CHECK_REPORT.md docs/audits/ || true
git mv SECURITY_AND_CODE_QUALITY_FIXES.md docs/audits/ || true

# Move reports
git mv DASHBOARD_FIX_INSTRUCTIONS.md docs/reports/ || true
git mv DATABASE_FIXES_SUMMARY.md docs/reports/ || true
git mv ENGINEER_REVIEW_RESULTS.md docs/reports/ || true
git mv FINANCIAL_CALCULATIONS_REFACTOR.md docs/reports/ || true
git mv FIXES_COMPLETE_SUMMARY.md docs/reports/ || true
git mv CLEANUP_SUMMARY.md docs/reports/ || true
git mv LEGACY_REMOVAL_COMPLETE.md docs/reports/ || true
git mv REFACTORING_PHASE1_REPORT.md docs/reports/ || true
git mv TWO_STAGE_FILTERING.md docs/reports/ || true
git mv VERIFY_UI_INTEGRATION.md docs/reports/ || true

# Move setup guides
git mv GITHUB_CODESPACES_SETUP.md docs/setup/ || true

# Move reference docs
git mv CRITICAL_DO_NOT_CHANGE.md docs/reference/ || true
git mv DOCUMENTATION_STATUS.md docs/reference/ || true

# Move config documentation
git mv config/NEW_STRUCTURE.md docs/architecture/config_structure.md || true

# Move SQL query samples
git mv data/INVENTORY_QUERY.md docs/queries/INVENTORY_QUERY.md || true

# Move miscellaneous guides
git mv docs/new_features_explanation.md docs/guides/ || true

# Remove agent/assistant files
git rm -f agent.md CLAUDE.md || true

echo "Documentation reorganized into docs/ hierarchy. Review and commit changes accordingly."