CREATE TABLE mvp_records (id TEXT PRIMARY KEY, code TEXT UNIQUE NOT NULL, owner TEXT NOT NULL, buyer TEXT, data TEXT NOT NULL);
CREATE TABLE mvp_commands (actor TEXT NOT NULL, key TEXT NOT NULL, body_hash TEXT NOT NULL, result TEXT NOT NULL, PRIMARY KEY(actor,key));
