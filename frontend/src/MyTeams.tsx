import { Link, useSearchParams } from 'react-router-dom';
import { useResource } from './use-resource';
import { EmptyState, PageHeading, PageLoading, ProjectCard } from './ui';
import type { MyTeam, Page, Project } from './types';

export function MyTeams() {
    const [params, setParams] = useSearchParams();
    const query = new URLSearchParams({ limit: '12' });
    for (const name of ['status', 'cursor']) if (params.get(name)) query.set(name, params.get(name)!);
    const teams = useResource<Page<MyTeam>>(`/me/teams?${query}`);
    const statuses: Project['status'][] = ['draft', 'open', 'in_progress', 'completed', 'archived'];
    function page(cursor?: string) {
        const next = new URLSearchParams(params);
        if (cursor) next.set('cursor', cursor); else next.delete('cursor');
        setParams(next);
    }
    return <main className="app-page">
        <PageHeading eyebrow="Collaboration" title="My teams" description="The projects you own and the teams you’re part of, all in one place." />
        <div className="list-toolbar"><label>Project status<select value={params.get('status') || ''} onChange={event => setParams(event.target.value ? { status: event.target.value } : {})}>
            <option value="">All statuses</option>{statuses.map(status => <option key={status} value={status}>{status.replaceAll('_', ' ')}</option>)}
        </select></label><Link to="/my-applications">View application history</Link></div>
        {teams.loading && <PageLoading>Loading your teams…</PageLoading>}
        {teams.error && <p role="alert">{teams.error.message} <button onClick={teams.reload}>Retry teams</button></p>}
        {teams.data?.items.length === 0 && <EmptyState title={params.has('status') ? 'No teams with this status' : 'Find your next team'} description="Accepted applications appear here while you’re a member. Your own projects appear here too."><Link className="button" to="/main">Explore projects</Link></EmptyState>}
        <div className="project-cards">{teams.data?.items.map(item => <div className="team-project" key={item.project.id}>
            <p className="team-role">{item.is_owner ? 'Project owner' : 'Team member'}{item.joined_at && ` · Joined ${new Date(item.joined_at).toLocaleDateString()}`}</p>
            <ProjectCard project={item.project}><Link to={`/projects/${item.project.id}/team`}>View team</Link></ProjectCard>
        </div>)}</div>
        {teams.data && <nav className="pagination" aria-label="Team pages">{params.has('cursor') && <button onClick={() => page()}>First page</button>}{teams.data.next_cursor && <button onClick={() => page(teams.data!.next_cursor!)}>Next page</button>}</nav>}
    </main>;
}
