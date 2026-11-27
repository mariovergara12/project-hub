import type { FormEvent } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useResource } from './use-resource';
import { loadCatalog } from './api';
import { EmptyState, Icon, PageLoading, ProjectCard } from './ui';
import { ProjectSearch } from './ProjectSearch';
import type { CatalogItem, Page, Project } from './types';

export function ProjectHub() {
    const [params, setParams] = useSearchParams();
    const query = new URLSearchParams(params);
    query.set('limit', '12');
    const projects = useResource<Page<Project>>(`/projects?${query}`);
    const skills = useResource<Page<CatalogItem>>('/skills', loadCatalog);
    const interests = useResource<Page<CatalogItem>>('/interests', loadCatalog);
    const advancedCount = ['status', 'skill_id', 'interest_id'].filter(name => params.has(name)).length;
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
    function changeType(type: string) {
        const next = new URLSearchParams(params);
        if (type) next.set('project_type', type); else next.delete('project_type');
        next.delete('cursor');
        setParams(next);
    }
    function searchProjects(value: string) {
        const next = new URLSearchParams(params);
        if (value) next.set('q', value); else next.delete('q');
        next.delete('cursor');
        setParams(next);
    }
    return <main className="app-page">
        <header className="dashboard-welcome"><span className="welcome-label"><Icon name="team" />Your campus, connected</span><h1>Find a project. Make it happen.</h1><p>Explore student projects and faculty research, or bring your own idea.</p></header>
        <ProjectSearch key={`project-search:${params.get('q') || ''}`} initialQuery={params.get('q') || ''} onSearch={searchProjects} />
        <form onSubmit={search} key={`filters:${params.toString()}`}>
            <input type="hidden" name="q" value={params.get('q') || ''} />
            <input type="hidden" name="project_type" value={params.get('project_type') || ''} />
            <details className="filter-details" open={advancedCount > 0 || undefined}>
                <summary>Refine your search{advancedCount ? ` · ${advancedCount} active` : ''}</summary>
                <div className="filters">
                    <label>Status<select name="status" defaultValue={params.get('status') || ''}><option value="">All visible projects</option><option value="open">Open</option><option value="draft">Draft</option><option value="in_progress">In progress</option><option value="completed">Completed</option><option value="archived">Archived</option></select></label>
                    <label>Skill<select name="skill_id" defaultValue={params.get('skill_id') || ''} disabled={!skills.data}><option value="">{skills.loading ? 'Loading skills…' : 'Any skill'}</option>{skills.data?.items.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
                    <label>Interest<select name="interest_id" defaultValue={params.get('interest_id') || ''} disabled={!interests.data}><option value="">{interests.loading ? 'Loading interests…' : 'Any interest'}</option>{interests.data?.items.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
                    <button type="submit">Apply filters</button><button type="button" onClick={() => setParams({})}>Clear filters</button>
                </div>
            </details>
        </form>
        <div className="filter-controls"><div className="type-tabs" role="group" aria-label="Project type">{[['', 'All opportunities'], ['student_project', 'Student projects'], ['research_opportunity', 'Faculty research']].map(([value, label]) => <button key={value} type="button" aria-pressed={(params.get('project_type') || '') === value} onClick={() => changeType(value)}>{label}</button>)}</div><span className="results-label">{projects.data ? `${projects.data.items.length} on this page` : 'Exploring opportunities'}</span></div>
        {skills.error && <p role="alert">Skills: {skills.error.message} <button onClick={skills.reload}>Retry skills</button></p>}
        {interests.error && <p role="alert">Interests: {interests.error.message} <button onClick={interests.reload}>Retry interests</button></p>}
        <section aria-label="Projects" aria-busy={projects.loading}>
            {projects.loading && <PageLoading>Loading projects…</PageLoading>}
            {projects.error && <p role="alert">{projects.error.message} <button onClick={projects.reload}>Retry projects</button></p>}
            {projects.data?.items.length === 0 && <EmptyState title="No projects found" description="Try a broader search or clear your filters to explore more opportunities."><button onClick={() => setParams({})}>Clear filters</button></EmptyState>}
            <div className="project-cards">{projects.data?.items.map(project => <ProjectCard key={project.id} project={project} />)}</div>
            <nav aria-label="Project pages" className="pagination">
                {params.has('cursor') && <button onClick={() => { const next = new URLSearchParams(params); next.delete('cursor'); setParams(next); }}>First page</button>}
                {projects.data?.next_cursor && <button onClick={() => { const next = new URLSearchParams(params); next.set('cursor', projects.data!.next_cursor!); setParams(next); }}>Next page <Icon name="arrow" /></button>}
            </nav>
        </section>
    </main>;
}
