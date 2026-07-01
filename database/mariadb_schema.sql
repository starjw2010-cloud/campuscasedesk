-- CampusCase Desk MariaDB schema
-- Purpose: make the synthetic JSONL demo portable to a real relational backend.
-- Charset/collation are set for Korean Slack/customer data.

CREATE TABLE IF NOT EXISTS users (
  user_id VARCHAR(64) PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  email VARCHAR(255),
  role VARCHAR(80),
  department VARCHAR(120),
  manager_user_id VARCHAR(64),
  domains JSON,
  source_type VARCHAR(40) NOT NULL DEFAULT 'synthetic_demo',
  payload JSON NOT NULL,
  INDEX idx_users_department (department),
  INDEX idx_users_manager (manager_user_id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS students (
  student_ref VARCHAR(80) PRIMARY KEY,
  name VARCHAR(120),
  masked_name VARCHAR(120),
  student_no_masked VARCHAR(80),
  department VARCHAR(120),
  year INT,
  nationality VARCHAR(80),
  source_type VARCHAR(40) NOT NULL DEFAULT 'synthetic_demo',
  payload JSON NOT NULL,
  INDEX idx_students_name (name),
  INDEX idx_students_department (department)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS channels (
  channel_id VARCHAR(80) PRIMARY KEY,
  name VARCHAR(160) NOT NULL,
  ko_label VARCHAR(160),
  domain VARCHAR(80),
  purpose TEXT,
  members JSON,
  source_type VARCHAR(40) NOT NULL DEFAULT 'synthetic_demo',
  payload JSON NOT NULL,
  INDEX idx_channels_domain (domain),
  INDEX idx_channels_name (name)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS canvases (
  canvas_id VARCHAR(80) PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  domain VARCHAR(80),
  channel_id VARCHAR(80),
  channel_name VARCHAR(160),
  related_case_ids JSON,
  markdown MEDIUMTEXT,
  source_type VARCHAR(40) NOT NULL DEFAULT 'synthetic_demo',
  payload JSON NOT NULL,
  INDEX idx_canvases_domain (domain),
  INDEX idx_canvases_channel (channel_id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS cases (
  case_id VARCHAR(80) PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  domain VARCHAR(80) NOT NULL,
  case_type VARCHAR(100) NOT NULL,
  status VARCHAR(80) NOT NULL,
  priority VARCHAR(40),
  risk_level VARCHAR(40),
  student_ref VARCHAR(80),
  student_name VARCHAR(120),
  owner_user_id VARCHAR(64),
  owner_name VARCHAR(120),
  approver_user_id VARCHAR(64),
  approver_name VARCHAR(120),
  related_channel_id VARCHAR(80),
  related_channel_name VARCHAR(160),
  related_thread_id VARCHAR(100),
  related_canvas_id VARCHAR(80),
  related_canvas_title VARCHAR(255),
  consent_on_file BOOLEAN,
  required_documents JSON,
  submitted_documents JSON,
  missing_documents JSON,
  related_rag_paths JSON,
  next_actions JSON,
  next_action TEXT,
  summary TEXT,
  timeline JSON,
  created_at_text VARCHAR(40),
  updated_at_text VARCHAR(40),
  source_type VARCHAR(40) NOT NULL DEFAULT 'synthetic_demo',
  payload JSON NOT NULL,
  INDEX idx_cases_domain_status (domain, status),
  INDEX idx_cases_owner (owner_user_id),
  INDEX idx_cases_approver (approver_user_id),
  INDEX idx_cases_student (student_ref),
  INDEX idx_cases_priority_risk (priority, risk_level),
  INDEX idx_cases_thread (related_thread_id),
  CONSTRAINT fk_cases_student_ref FOREIGN KEY (student_ref) REFERENCES students(student_ref) ON DELETE SET NULL
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tasks (
  task_id VARCHAR(80) PRIMARY KEY,
  case_id VARCHAR(80) NOT NULL,
  title VARCHAR(255) NOT NULL,
  owner_user_id VARCHAR(64),
  owner_name VARCHAR(120),
  status VARCHAR(80) NOT NULL,
  priority VARCHAR(40),
  due_at VARCHAR(40),
  created_at VARCHAR(40),
  source_type VARCHAR(40) NOT NULL DEFAULT 'synthetic_demo',
  payload JSON NOT NULL,
  INDEX idx_tasks_case (case_id),
  INDEX idx_tasks_owner_status (owner_user_id, status),
  INDEX idx_tasks_due (due_at),
  CONSTRAINT fk_tasks_case_id FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS approvals (
  approval_id VARCHAR(80) PRIMARY KEY,
  case_id VARCHAR(80) NOT NULL,
  type VARCHAR(120),
  requester_user_id VARCHAR(64),
  requester_name VARCHAR(120),
  approver_user_id VARCHAR(64),
  approver_name VARCHAR(120),
  status VARCHAR(80) NOT NULL,
  requested_at VARCHAR(40),
  decided_at VARCHAR(40),
  due_at VARCHAR(40),
  comment TEXT,
  source_type VARCHAR(40) NOT NULL DEFAULT 'synthetic_demo',
  payload JSON NOT NULL,
  INDEX idx_approvals_case (case_id),
  INDEX idx_approvals_approver_status (approver_user_id, status),
  INDEX idx_approvals_due_status (due_at, status),
  CONSTRAINT fk_approvals_case_id FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS documents (
  document_id VARCHAR(80) PRIMARY KEY,
  case_id VARCHAR(80) NOT NULL,
  doc_type VARCHAR(160),
  title VARCHAR(255),
  status VARCHAR(80) NOT NULL,
  student_ref VARCHAR(80),
  owner_user_id VARCHAR(64),
  rag_path VARCHAR(255),
  file_ref VARCHAR(255),
  pii_masked BOOLEAN,
  consent_required BOOLEAN,
  created_at VARCHAR(40),
  source_type VARCHAR(40) NOT NULL DEFAULT 'synthetic_demo',
  payload JSON NOT NULL,
  INDEX idx_documents_case (case_id),
  INDEX idx_documents_status (status),
  INDEX idx_documents_owner (owner_user_id),
  INDEX idx_documents_rag_path (rag_path),
  CONSTRAINT fk_documents_case_id FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS relationships (
  rel_id VARCHAR(100) PRIMARY KEY,
  from_id VARCHAR(100) NOT NULL,
  from_type VARCHAR(80) NOT NULL,
  to_id VARCHAR(100) NOT NULL,
  to_type VARCHAR(80) NOT NULL,
  relation VARCHAR(100) NOT NULL,
  source_type VARCHAR(40) NOT NULL DEFAULT 'synthetic_demo',
  payload JSON NOT NULL,
  INDEX idx_relationships_from (from_id, from_type),
  INDEX idx_relationships_to (to_id, to_type),
  INDEX idx_relationships_relation (relation)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS slack_threads (
  thread_id VARCHAR(100) PRIMARY KEY,
  case_id VARCHAR(80),
  title VARCHAR(255),
  channel_id VARCHAR(80),
  channel_name VARCHAR(160),
  participants JSON,
  message_count INT,
  messages JSON,
  created_at VARCHAR(40),
  source_type VARCHAR(40) NOT NULL DEFAULT 'synthetic_demo',
  payload JSON NOT NULL,
  INDEX idx_threads_case (case_id),
  INDEX idx_threads_channel (channel_id),
  CONSTRAINT fk_threads_case_id FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE SET NULL
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS rag_documents (
  path VARCHAR(255) PRIMARY KEY,
  doc_id VARCHAR(120),
  domain VARCHAR(80),
  title VARCHAR(255),
  applies_to_case_types JSON,
  source_type VARCHAR(40) NOT NULL DEFAULT 'synthetic_demo',
  body MEDIUMTEXT,
  payload JSON NOT NULL,
  INDEX idx_rag_documents_domain (domain),
  INDEX idx_rag_documents_doc_id (doc_id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS workspace_map (
  workspace_key VARCHAR(120) PRIMARY KEY,
  generated_at VARCHAR(40),
  source_type VARCHAR(40) NOT NULL DEFAULT 'synthetic_demo',
  payload JSON NOT NULL
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS audit_logs (
  audit_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  actor_user_id VARCHAR(64),
  action VARCHAR(120) NOT NULL,
  entity_type VARCHAR(80),
  entity_id VARCHAR(100),
  details JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  source_type VARCHAR(40) NOT NULL DEFAULT 'synthetic_demo',
  INDEX idx_audit_entity (entity_type, entity_id),
  INDEX idx_audit_actor (actor_user_id),
  INDEX idx_audit_created_at (created_at)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE OR REPLACE VIEW case_document_summary AS
SELECT
  c.case_id,
  c.title,
  c.domain,
  c.status AS case_status,
  c.owner_user_id,
  c.owner_name,
  COUNT(d.document_id) AS document_count,
  SUM(CASE WHEN d.status IN ('미제출', 'missing', 'requested') THEN 1 ELSE 0 END) AS missing_document_count
FROM cases c
LEFT JOIN documents d ON d.case_id = c.case_id
GROUP BY c.case_id, c.title, c.domain, c.status, c.owner_user_id, c.owner_name;

CREATE OR REPLACE VIEW approval_due_summary AS
SELECT
  a.approval_id,
  a.case_id,
  c.title AS case_title,
  c.domain,
  c.priority,
  c.risk_level,
  a.approver_user_id,
  a.approver_name,
  a.status,
  a.due_at
FROM approvals a
JOIN cases c ON c.case_id = a.case_id;
