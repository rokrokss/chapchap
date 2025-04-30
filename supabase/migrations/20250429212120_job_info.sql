CREATE SCHEMA IF NOT EXISTS chapssal;

-- Create job_info table
CREATE TABLE chapssal.job_info (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    job_title TEXT NOT NULL,
    company_name TEXT NOT NULL,
    affiliate_company_name TEXT NOT NULL,
    link TEXT NOT NULL UNIQUE,
    team_info TEXT NOT NULL,
    responsibilities TEXT NOT NULL,
    qualifications TEXT NOT NULL,
    preferred_qualifications TEXT NOT NULL,
    hiring_process TEXT[] NOT NULL,
    additional_info TEXT NOT NULL,
    uploaded_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

-- Create index for faster searches
CREATE INDEX idx_job_info_job_title ON chapssal.job_info(job_title);
CREATE INDEX idx_job_info_company_name ON chapssal.job_info(company_name);
CREATE INDEX idx_job_info_job_title_company_name ON chapssal.job_info(job_title, company_name);
CREATE INDEX idx_job_info_uploaded_date ON chapssal.job_info(uploaded_date);
CREATE INDEX idx_job_info_is_active ON chapssal.job_info(is_active);
CREATE INDEX idx_job_info_link ON chapssal.job_info(link);

-- Add RLS policies
ALTER TABLE chapssal.job_info ENABLE ROW LEVEL SECURITY;

-- Allow public read access
CREATE POLICY "Allow public read access" ON chapssal.job_info
    FOR SELECT
    USING (true);

-- Allow authenticated users to insert
CREATE POLICY "Allow authenticated users to insert" ON chapssal.job_info
    FOR INSERT
    TO authenticated
    WITH CHECK (true);

-- Allow authenticated users to update their own posts
CREATE POLICY "Allow authenticated users to update" ON chapssal.job_info
    FOR UPDATE
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Allow authenticated users to delete their own posts
CREATE POLICY "Allow authenticated users to delete" ON chapssal.job_info
    FOR DELETE
    TO authenticated
    USING (true);
