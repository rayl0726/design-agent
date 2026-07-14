ALTER TABLE java_projects
  ADD COLUMN agent_type VARCHAR(30) NOT NULL DEFAULT 'generic',
  ADD COLUMN agent_context_json TEXT;
