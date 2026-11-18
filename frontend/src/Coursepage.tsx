import type { FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { AccountAccess } from './AccountAccess';
import { useResource } from './use-resource';
import { loadCatalog } from './api';
import type { CatalogItem, Page, Project } from './types';

export function ProjectHub() {
    const [params, setParams] = useSearchParams();
    const query = new URLSearchParams(params);
    query.set('limit', '3');
    const projects = useResource<Page<Project>>(`/projects?${query}`);
    const skills = useResource<Page<CatalogItem>>('/skills', loadCatalog);
    const interests = useResource<Page<CatalogItem>>('/interests', loadCatalog);
    function search(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        const next = new URLSearchParams();
        for (const name of ['q', 'project_type', 'status', 'skill_id', 'interest_id']) {
            const value = String(form.get(name) || '').trim();
            if (value) next.set(name, value);
        }
        setParams(next);
    }
    return <main className="app-page">
        <header className="app-header"><h1>Project Hub</h1><nav><Link to="/my-projects">My Projects</Link> · <Link to="/my-applications">My Applications</Link> · <Link to="/projects/new">Create project</Link> · <Link to="/profile">Your profile</Link></nav></header>
        <AccountAccess />
        <form onSubmit={search} className="filters" key={params.toString()}>
            <label>Search projects<input name="q" maxLength={200} placeholder="Title or description" defaultValue={params.get('q') || ''} /></label>
            <label>Project type<select name="project_type" defaultValue={params.get('project_type') || ''}>
                <option value="">All types</option><option value="student_project">Student projects</option>
                <option value="research_opportunity">Research opportunities</option>
            </select></label>
            <label>Status<select name="status" defaultValue={params.get('status') || ''}>
                <option value="">All visible projects</option><option value="open">Open</option>
                <option value="draft">Draft</option><option value="in_progress">In progress</option>
                <option value="completed">Completed</option><option value="archived">Archived</option>
            </select></label>
            <label>Skill<select name="skill_id" defaultValue={params.get('skill_id') || ''} disabled={!skills.data}>
                <option value="">{skills.loading ? 'Loading skills…' : 'Any skill'}</option>
                {skills.data?.items.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select></label>
            <label>Interest<select name="interest_id" defaultValue={params.get('interest_id') || ''} disabled={!interests.data}>
                <option value="">{interests.loading ? 'Loading interests…' : 'Any interest'}</option>
                {interests.data?.items.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select></label>
            <button type="submit">Apply filters</button>
            <button type="button" onClick={() => setParams({})}>Clear filters</button>
        </form>
        {skills.error && <p role="alert">Skills: {skills.error.message} <button onClick={skills.reload}>Retry skills</button></p>}
        {interests.error && <p role="alert">Interests: {interests.error.message} <button onClick={interests.reload}>Retry interests</button></p>}
        <section aria-label="Projects" aria-busy={projects.loading}>
            {projects.loading && <p role="status">Loading projects…</p>}
            {projects.error && <p role="alert">{projects.error.message} <button onClick={projects.reload}>Retry projects</button></p>}
            {projects.data?.items.length === 0 && <p>No projects match these filters.</p>}
            <div className="project-cards">
                {projects.data?.items.map(project => <article key={project.id} className="project-card">
                    <p className="project-meta">{project.project_type.replaceAll('_', ' ')} · {project.status.replaceAll('_', ' ')}</p>
                    <h2><Link to={`/projects/${project.id}`}>{project.title}</Link></h2>
                    <p>{project.description}</p>
                    <p>By {project.owner.display_name || 'Project owner'}{project.owner.faculty_verified ? ' · Verified faculty' : ''}</p>
                    <p>{project.weekly_hours === null ? 'Hours unspecified' : `${project.weekly_hours} hours/week`} · {project.member_count}{project.max_members === null ? ' members' : ` / ${project.max_members} members`}</p>
                    <p>{project.skills.map(skill => skill.name).join(', ') || 'No skills listed'}</p>
                </article>)}
            </div>
            <nav aria-label="Project pages" className="pagination">
                {params.has('cursor') && <button onClick={() => { const next = new URLSearchParams(params); next.delete('cursor'); setParams(next); }}>First page</button>}
                {projects.data?.next_cursor && <button onClick={() => { const next = new URLSearchParams(params); next.set('cursor', projects.data!.next_cursor!); setParams(next); }}>Next page</button>}
            </nav>
        </section>
    </main>;
}
