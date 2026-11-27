import { Link, useSearchParams } from 'react-router-dom';
import { useResource } from './use-resource';
import { EmptyState, Icon, PageHeading, PageLoading, ProjectCard } from './ui';
import type { Page, Project } from './types';

export function MyProjects() {
    const [params, setParams] = useSearchParams();
    const query = new URLSearchParams({ limit: '10' });
    for (const name of ['status', 'cursor']) if (params.get(name)) query.set(name, params.get(name)!);
    const projects = useResource<Page<Project>>(`/me/projects?${query}`);
    return <main className="app-page">
        <PageHeading eyebrow="Your workspace" title="My projects" description="The ideas you're bringing to life. Manage your drafts, find collaborators, and keep things moving." actions={<Link className="button" to="/projects/new"><Icon name="plus" />Create project</Link>} />
        <div className="list-toolbar"><label>Status<select value={params.get('status') || ''} onChange={event => setParams(event.target.value ? { status: event.target.value } : {})}>
            <option value="">All statuses</option>{['draft','open','in_progress','completed','archived'].map(status => <option key={status} value={status}>{status.replaceAll('_', ' ')}</option>)}
        </select></label><span className="results-label">Owned projects · Includes private drafts</span></div>
        {projects.loading && <PageLoading>Loading your projects…</PageLoading>}
        {projects.error && <p role="alert">{projects.error.message} <button onClick={projects.reload}>Retry projects</button></p>}
        {projects.data?.items.length === 0 && <EmptyState title="Room for your next idea" description="Create a private draft, add the details, and publish when you're ready."><Link className="button button-primary" to="/projects/new">Create a draft <Icon name="arrow" /></Link></EmptyState>}
        <div className="project-cards">{projects.data?.items.map(project => <ProjectCard key={project.id} project={project} editable />)}</div>
        <nav aria-label="My project pages" className="pagination">
            {params.has('cursor') && <button onClick={() => { const next = new URLSearchParams(params); next.delete('cursor'); setParams(next); }}>First page</button>}
            {projects.data?.next_cursor && <button onClick={() => { const next = new URLSearchParams(params); next.set('cursor', projects.data!.next_cursor!); setParams(next); }}>Next page</button>}
        </nav>
    </main>;
}
