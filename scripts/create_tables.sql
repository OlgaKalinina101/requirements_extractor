-- Requirements Management System - Database Schema
-- Hierarchy: Project -> Document -> Section -> Requirement

-- Create projects table
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(100) UNIQUE,
    description TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_projects_id ON projects(id);
CREATE INDEX IF NOT EXISTS ix_projects_code ON projects(code);

-- Create documents table
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    total_pages INTEGER,
    model_used VARCHAR(100),
    uploaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_documents_id ON documents(id);

-- Create sections table
CREATE TABLE IF NOT EXISTS sections (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    section_number VARCHAR(50),
    title TEXT,
    page_start INTEGER,
    page_end INTEGER
);

CREATE INDEX IF NOT EXISTS ix_sections_id ON sections(id);

-- Create requirements table
CREATE TABLE IF NOT EXISTS requirements (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    section_id INTEGER REFERENCES sections(id) ON DELETE SET NULL,
    requirement_id VARCHAR(50) NOT NULL,
    text TEXT NOT NULL,
    type VARCHAR(50),
    priority VARCHAR(50),
    page_number INTEGER,
    bbox JSONB,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    ai_suggested TEXT NOT NULL,
    human_edited TEXT,
    edit_reason TEXT,
    edited_by VARCHAR(255),
    edited_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_requirements_id ON requirements(id);
CREATE INDEX IF NOT EXISTS ix_requirements_requirement_id ON requirements(requirement_id);
CREATE INDEX IF NOT EXISTS ix_requirements_status ON requirements(status);

-- Create coverage_metrics table
CREATE TABLE IF NOT EXISTS coverage_metrics (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL UNIQUE REFERENCES documents(id) ON DELETE CASCADE,
    total_pages INTEGER NOT NULL,
    processed_pages INTEGER NOT NULL,
    skipped_pages INTEGER[],
    coverage_percent FLOAT NOT NULL,
    requirements_count INTEGER NOT NULL,
    requirements_by_type JSONB,
    calculated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_coverage_metrics_id ON coverage_metrics(id);

-- Verify tables were created
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
