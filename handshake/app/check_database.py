"""Read-only local integrity, journal, receipt and instruction reconciliation check."""
import json
import sys
import server as app

with app.connection() as db:
    integrity=db.execute('PRAGMA integrity_check').fetchone()[0]
    unbalanced=[dict(x) for x in db.execute('SELECT journal,SUM(amount) AS difference FROM ledger GROUP BY journal HAVING SUM(amount)!=0')]
    unmatched=[dict(x) for x in db.execute("SELECT c.record_id,c.amount,COALESCE(SUM(l.amount),0) AS posted FROM callbacks c LEFT JOIN ledger l ON c.record_id=l.record_id AND l.account='provider_cash' AND l.journal LIKE 'collection:%' GROUP BY c.receipt_id HAVING c.amount!=COALESCE(SUM(l.amount),0)")]
    instruction_differences=[dict(x) for x in db.execute('SELECT p.reference,p.outcome,j.state FROM provider_instructions p JOIN jobs j ON j.id=p.job_id WHERE p.outcome!=j.state')]
    balances={x['account']:x['balance'] for x in db.execute('SELECT account,SUM(amount) AS balance FROM ledger GROUP BY account')}
    result=dict(integrity=integrity,migrations=[x[0] for x in db.execute('SELECT version FROM schema_migrations ORDER BY version')],unbalanced_journals=unbalanced,receipt_differences=unmatched,instruction_differences=instruction_differences,balances=balances,liquidity={'available':app.available_float(db),'capacity':int(app.settings(db,'float'))},open_cases=db.execute("SELECT COUNT(*) FROM records WHERE json_extract(data,'$.case_open')=1").fetchone()[0],pending_or_unknown_jobs=db.execute("SELECT COUNT(*) FROM jobs WHERE state IN ('pending','unknown')").fetchone()[0])
print(json.dumps(result,indent=2))
sys.exit(0 if integrity=='ok' and not unbalanced and not unmatched and not instruction_differences else 1)
