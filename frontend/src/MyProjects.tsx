import { Link, useSearchParams } from 'react-router-dom';
import { AccountAccess } from './AccountAccess';
import { useResource } from './use-resource';
import type { Page, Project } from './types';

export function MyProjects() {
    const [params, setParams] = useSearchParams();
    const query = new URLSearchParams({ limit: '10' });
    for (const name of ['status', 'cursor']) if (params.get(name)) query.set(name, params.get(name)!);
    const projects = useResource<Page<Project>>(`/me/projects?${query}`);
    return <main className="app-page">
        <header><h1>My Projects</h1><nav><Link to="/main">Project Hub</Link> · <Link to="/my-applications">My Applications</Link> · <Link to="/projects/new">Create project</Link></nav></header>
        <AccountAccess />
        <p>Projects you own, including drafts and archived projects.</p>
        <label>Status<select value={params.get('status') || ''} onChange={event => setParams(event.target.value ? { status: event.target.value } : {})}>
            <option value="">All statuses</option>
            {['draft','open','in_progress','completed','archived'].map(status => <option key={status} value={status}>{status.replaceAll('_',' ')}</option>)}
        </select></label>
        {projects.loading && <p role="status">Loading your projects…</p>}
        {projects.error && <p role="alert">{projects.error.message} <button onClick={projects.reload}>Retry projects</button></p>}
        {projects.data?.items.length === 0 && <p>No projects to show. <Link to="/projects/new">Create a draft</Link></p>}
        <div className="project-cards">{projects.data?.items.map(project => <article key={project.id} className="project-card">
            <h2><Link to={`/projects/${project.id}`}>{project.title}</Link></h2>
            <p>{project.status.replaceAll('_', ' ')} · {project.member_count} {project.member_count === 1 ? 'member' : 'members'}{project.max_members === null ? '' : ` / ${project.max_members} capacity`}</p>
            <p>{project.description}</p>
            {project.status !== 'archived' && <Link to={`/projects/${project.id}/edit`}>Edit project</Link>}
        </article>)}</div>
        <nav aria-label="My project pages" className="pagination">
            {params.has('cursor') && <button onClick={() => { const next = new URLSearchParams(params); next.delete('cursor'); setParams(next); }}>First page</button>}
            {projects.data?.next_cursor && <button onClick={() => { const next = new URLSearchParams(params); next.set('cursor', projects.data!.next_cursor!); setParams(next); }}>Next page</button>}
        </nav>
    </main>;
}
