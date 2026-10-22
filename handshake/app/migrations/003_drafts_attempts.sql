CREATE TABLE drafts(actor TEXT NOT NULL, kind TEXT NOT NULL, data TEXT NOT NULL, updated INTEGER NOT NULL, PRIMARY KEY(actor,kind));
CREATE TABLE collection_attempts(reference TEXT PRIMARY KEY, record_id TEXT NOT NULL, method TEXT NOT NULL, quote TEXT NOT NULL, created INTEGER NOT NULL);
CREATE TRIGGER no_attempt_update BEFORE UPDATE ON collection_attempts BEGIN SELECT RAISE(ABORT,'Collection attempts are immutable'); END;
CREATE TRIGGER no_attempt_delete BEFORE DELETE ON collection_attempts BEGIN SELECT RAISE(ABORT,'Collection attempts are immutable'); END;
