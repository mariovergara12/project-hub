export type Role = 'student' | 'faculty' | 'administrator';
export type ProfileData = {
    user_id: string; display_name: string; university: string | null;
    major: string | null; department: string | null; bio: string | null;
    availability_hours: number | null; learning_goals: string | null; experience_years: number | null;
};
export type Me = {
    id: string; role: Role; faculty_verified_at: string | null; profile: ProfileData | null;
    skills: CatalogItem[]; interests: CatalogItem[];
};
export type CatalogItem = { id: string; name: string };
export type Page<T> = { items: T[]; next_cursor: string | null };
export type Project = {
    id: string; title: string; description: string;
    project_type: 'student_project' | 'research_opportunity';
    status: 'draft' | 'open' | 'in_progress' | 'completed' | 'archived';
    weekly_hours: number | null; minimum_experience_years: number | null;
    max_members: number | null; member_count: number;
    owner: { id: string; display_name: string | null; role: Role; faculty_verified: boolean };
    skills: (CatalogItem & { required: boolean })[]; interests: CatalogItem[];
    created_at: string; updated_at: string;
};
export type ApplicationStatus = 'pending' | 'accepted' | 'rejected' | 'withdrawn';
export type ProjectSummary = Pick<Project, 'id' | 'title' | 'status'> & { owner_id: string };
export type ApplicationRecord = {
    id: string; project: ProjectSummary; applicant: Project['owner']; message: string | null;
    status: ApplicationStatus; created_at: string; updated_at: string;
};
export type ProjectApplications = Page<ApplicationRecord> & { project: ProjectSummary };
export type Member = { user: Project['owner']; joined_at: string; is_owner: boolean };
export type Team = Page<Member> & { project: ProjectSummary; member_count: number; max_members: number | null };
export type MyTeam = { project: Project; joined_at: string | null; is_owner: boolean };
export type MilestoneStatus = 'todo' | 'in_progress' | 'completed';
export type Milestone = {
    id: string; project_id: string; title: string; description: string | null;
    due_date: string | null; status: MilestoneStatus; created_at: string; updated_at: string;
};
export type MilestonePage = Page<Milestone> & {
    project: ProjectSummary;
    progress: { total: number; todo: number; in_progress: number; completed: number };
};
export type RecommendationProfileField = 'skills' | 'interests' | 'availability_hours' | 'experience_years';
export type ProjectRecommendation = { project: Project; score: number; reasons: string[]; cautions: string[] };
export type RecommendedProjects = { items: ProjectRecommendation[]; missing_fields: RecommendationProfileField[] };
