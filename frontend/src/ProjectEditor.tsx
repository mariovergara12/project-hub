import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { AccountAccess } from './AccountAccess';
import { api, loadCatalog } from './api';
import { useResource } from './use-resource';
import type { CatalogItem, Me, Page, Project } from './types';

export function ProjectEditor() {
    const { projectId } = useParams();
    const me = useResource<Me>('/me');
    return <main className="app-page">
        <header><h1>{projectId ? 'Edit project' : 'Create project'}</h1><Link to="/my-projects">My Projects</Link></header>
        <AccountAccess />
        {me.loading && <p role="status">Loading account…</p>}
        {me.error && <p role="alert">{me.error.message} <button onClick={me.reload}>Retry account</button></p>}
        {me.data && (projectId ? <ExistingProject key={projectId} id={projectId} me={me.data} /> : <ProjectForm key={me.data.id} me={me.data} />)}
    </main>;
}

function ExistingProject({ id, me }: { id: string; me: Me }) {
    const project = useResource<Project>(`/projects/${encodeURIComponent(id)}`);
    if (project.loading) return <p role="status">Loading project…</p>;
    if (project.error) return <p role="alert">{project.error.message} <button onClick={project.reload}>Retry project</button></p>;
    if (!project.data) return null;
    if (project.data.owner.id !== me.id) return <p role="alert">Only the project owner can edit this project.</p>;
    if (project.data.status === 'archived') return <p>Archived projects are read-only. <Link to={`/projects/${id}`}>View project</Link></p>;
    return <ProjectForm me={me} initial={project.data} />;
}

export function ProjectForm({ me, initial }: { me: Me; initial?: Project }) {
    const navigate = useNavigate();
    const skills = useResource<Page<CatalogItem>>('/skills', loadCatalog);
    const interests = useResource<Page<CatalogItem>>('/interests', loadCatalog);
    const [selectedSkills, setSkills] = useState<Record<string, 'required' | 'optional'>>(() => Object.fromEntries(initial?.skills.map(item => [item.id, item.required ? 'required' : 'optional']) || []));
    const [selectedInterests, setInterests] = useState(() => new Set(initial?.interests.map(item => item.id)));
    const [pending, setPending] = useState(false);
    const submitting = useRef(false);
    const request = useRef<AbortController | null>(null);
    useEffect(() => () => request.current?.abort(), []);
    const [error, setError] = useState('');
    const verified = me.role === 'faculty' && me.faculty_verified_at !== null;
    async function save(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (submitting.current || !skills.data || !interests.data) return;
        const form = new FormData(event.currentTarget);
        const number = (name: string) => String(form.get(name) || '').trim() === '' ? null : Number(form.get(name));
        const body = {
            title: String(form.get('title')).trim(), description: String(form.get('description')).trim(),
            project_type: String(form.get('project_type')), weekly_hours: number('weekly_hours'),
            minimum_experience_years: number('minimum_experience_years'), max_members: number('max_members'),
            skills: Object.entries(selectedSkills).map(([skill_id, kind]) => ({ skill_id, required: kind === 'required' })),
            interest_ids: [...selectedInterests],
        };
        const controller = new AbortController();
        request.current = controller;
        submitting.current = true;
        setPending(true);
        setError('');
        try {
            const result = initial
                ? await api.patch<Project>(`/projects/${initial.id}`, body, controller.signal)
                : await api.post<Project>('/projects', body, controller.signal);
            if (!controller.signal.aborted) navigate(`/projects/${result.id}`);
        } catch (cause) { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Could not save project.'); }
        finally { submitting.current = false; if (!controller.signal.aborted) setPending(false); }
    }
    return <>
        <p>{initial ? 'Save your project details below.' : 'New projects start as private drafts. Preview the draft before publishing.'} The owner counts as one team member.</p>
        {initial?.project_type === 'research_opportunity' && !verified && <p role="alert">Research edits require verified faculty. You can change this to a student project or archive it from its details page.</p>}
        {skills.loading || interests.loading ? <p role="status">Loading project options…</p> : null}
        {skills.error && <p role="alert">{skills.error.message} <button onClick={skills.reload}>Retry skills</button></p>}
        {interests.error && <p role="alert">{interests.error.message} <button onClick={interests.reload}>Retry interests</button></p>}
        <form onSubmit={save}>
            <fieldset className="profile-fields" disabled={pending || !skills.data || !interests.data}>
                <legend>Project details</legend>
                <label>Title<input name="title" required maxLength={200} defaultValue={initial?.title || ''} /></label>
                <label>Description<textarea name="description" required maxLength={10000} rows={5} defaultValue={initial?.description || ''} /></label>
                <label>Project type<select name="project_type" defaultValue={initial?.project_type || 'student_project'}>
                    <option value="student_project">Student project</option>
                    {(verified || initial?.project_type === 'research_opportunity') && <option value="research_opportunity" disabled={!verified}>Research opportunity</option>}
                </select></label>
                {!verified && <p>Research opportunities require verified faculty.</p>}
                <label>Weekly hours<input type="number" name="weekly_hours" min={0} max={168} step={1} defaultValue={initial?.weekly_hours ?? ''} /></label>
                <label>Minimum experience (years)<input type="number" name="minimum_experience_years" min={0} max={100} step={1} defaultValue={initial?.minimum_experience_years ?? ''} /></label>
                <label>Team capacity (including owner)<input type="number" name="max_members" min={initial?.member_count || 1} max={100} step={1} defaultValue={initial?.max_members ?? ''} /></label>
                <p>Leave numeric fields blank for unspecified values or no capacity limit.</p>
                <fieldset className="project-selections"><legend>Skills (up to 50)</legend>
                    {skills.data?.items.map(item => <label key={item.id}>{item.name}<select aria-label={`${item.name} requirement`} value={selectedSkills[item.id] || ''} disabled={!selectedSkills[item.id] && Object.keys(selectedSkills).length >= 50} onChange={event => {
                        const next = { ...selectedSkills };
                        if (event.target.value) next[item.id] = event.target.value as 'required' | 'optional'; else delete next[item.id];
                        setSkills(next);
                    }}><option value="">Not listed</option><option value="required">Required</option><option value="optional">Optional</option></select></label>)}
                </fieldset>
                <fieldset className="project-selections interests"><legend>Interests (up to 50)</legend>
                    {interests.data?.items.map(item => <label key={item.id}><input type="checkbox" checked={selectedInterests.has(item.id)} disabled={!selectedInterests.has(item.id) && selectedInterests.size >= 50} onChange={event => {
                        const next = new Set(selectedInterests);
                        if (event.target.checked) next.add(item.id); else next.delete(item.id);
                        setInterests(next);
                    }} />{item.name}</label>)}
                </fieldset>
                <button type="submit">{pending ? 'Saving project…' : initial ? 'Save project' : 'Create draft'}</button>
            </fieldset>
            {error && <p role="alert">{error}</p>}
        </form>
        <Link to={initial ? `/projects/${initial.id}` : '/my-projects'}>Cancel</Link>
    </>;
}
