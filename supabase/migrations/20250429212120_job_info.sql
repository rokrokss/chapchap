CREATE SCHEMA IF NOT EXISTS chapchap;

CREATE TABLE chapchap.companies (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE chapchap.affiliate_companies (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    parent_company_id INT NOT NULL REFERENCES chapchap.companies(id) ON DELETE CASCADE
);

CREATE TABLE chapchap.tags (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE chapchap.job_info (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    job_title TEXT NOT NULL,
    company_id INT NOT NULL REFERENCES chapchap.companies(id) ON DELETE CASCADE,
    affiliate_company_id INT NOT NULL REFERENCES chapchap.affiliate_companies(id) ON DELETE CASCADE,
    link TEXT NOT NULL UNIQUE,
    team_info TEXT NOT NULL,
    responsibilities TEXT[] NOT NULL,
    qualifications TEXT[] NOT NULL,
    preferred_qualifications TEXT[] NOT NULL,
    hiring_process TEXT[] NOT NULL,
    additional_info TEXT[] NOT NULL,
    uploaded_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

CREATE TABLE chapchap.job_tags (
    job_id UUID REFERENCES chapchap.job_info(id) ON DELETE CASCADE,
    tag_id INT REFERENCES chapchap.tags(id) ON DELETE CASCADE,
    PRIMARY KEY (job_id, tag_id)
);

-- Create index for faster searches
CREATE INDEX idx_affiliate_company_parent_company_id ON chapchap.affiliate_companies(parent_company_id);
CREATE INDEX idx_job_info_job_title ON chapchap.job_info(job_title);
CREATE INDEX idx_job_info_company_id ON chapchap.job_info(company_id);
CREATE INDEX idx_job_info_affiliate_company_id ON chapchap.job_info(affiliate_company_id);
CREATE INDEX idx_job_info_uploaded_date ON chapchap.job_info(uploaded_date DESC);
CREATE INDEX idx_job_info_updated_at ON chapchap.job_info(updated_at DESC);
CREATE INDEX idx_job_info_is_active ON chapchap.job_info(is_active);
CREATE INDEX idx_job_tags_job_id ON chapchap.job_tags (job_id);
CREATE INDEX idx_job_tags_tag_id ON chapchap.job_tags (tag_id);

-- Add RLS policies
ALTER TABLE chapchap.job_info ENABLE ROW LEVEL SECURITY;
ALTER TABLE chapchap.companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE chapchap.affiliate_companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE chapchap.tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE chapchap.job_tags ENABLE ROW LEVEL SECURITY;

-- Allow public read access
CREATE POLICY "Allow public read access" ON chapchap.job_info
    FOR SELECT
    USING (true);
CREATE POLICY "Allow public read access" ON chapchap.companies
    FOR SELECT
    USING (true);
CREATE POLICY "Allow public read access" ON chapchap.affiliate_companies
    FOR SELECT
    USING (true);
CREATE POLICY "Allow public read access" ON chapchap.tags
    FOR SELECT
    USING (true);
CREATE POLICY "Allow public read access" ON chapchap.job_tags
    FOR SELECT
    USING (true);

-- Allow authenticated users to insert
CREATE POLICY "Allow authenticated users to insert" ON chapchap.job_info
    FOR INSERT
    TO authenticated
    WITH CHECK (true);
CREATE POLICY "Allow authenticated users to insert" ON chapchap.companies
    FOR INSERT
    TO authenticated
    WITH CHECK (true);
CREATE POLICY "Allow authenticated users to insert" ON chapchap.affiliate_companies
    FOR INSERT
    TO authenticated
    WITH CHECK (true);
CREATE POLICY "Allow authenticated users to insert" ON chapchap.tags
    FOR INSERT
    TO authenticated
    WITH CHECK (true);
CREATE POLICY "Allow authenticated users to insert" ON chapchap.job_tags
    FOR INSERT
    TO authenticated
    WITH CHECK (true);

-- Allow authenticated users to update their own posts
CREATE POLICY "Allow authenticated users to update" ON chapchap.job_info
    FOR UPDATE
    TO authenticated
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow authenticated users to update" ON chapchap.companies
    FOR UPDATE
    TO authenticated
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow authenticated users to update" ON chapchap.affiliate_companies
    FOR UPDATE
    TO authenticated
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow authenticated users to update" ON chapchap.tags
    FOR UPDATE
    TO authenticated
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow authenticated users to update" ON chapchap.job_tags
    FOR UPDATE
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Allow authenticated users to delete their own posts
CREATE POLICY "Allow authenticated users to delete" ON chapchap.job_info
    FOR DELETE
    TO authenticated
    USING (true);

CREATE POLICY "Allow authenticated users to delete" ON chapchap.companies
    FOR DELETE
    TO authenticated
    USING (true);

CREATE POLICY "Allow authenticated users to delete" ON chapchap.affiliate_companies
    FOR DELETE
    TO authenticated
    USING (true);

CREATE POLICY "Allow authenticated users to delete" ON chapchap.tags
    FOR DELETE
    TO authenticated
    USING (true);

CREATE POLICY "Allow authenticated users to delete" ON chapchap.job_tags
    FOR DELETE
    TO authenticated
    USING (true);
