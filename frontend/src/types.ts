export type Role = 'student' | 'faculty' | 'administrator';
export type ProfileData = {
    user_id: string; display_name: string; university: string | null;
    major: string | null; department: string | null; bio: string | null;
    availability_hours: number | null; learning_goals: string | null; experience_years: number | null;
};
export type Me = { id: string; role: Role; faculty_verified_at: string | null; profile: ProfileData | null };
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
