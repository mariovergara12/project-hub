import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from './api';
import { ApiError } from './lib/api-client';
import { refreshResources, useResource } from './use-resource';
import { Icon, PageHeading, PageLoading, StatusBadge } from './ui';
import { ConfirmDialog } from './ConfirmDialog';
import type { Me, Project } from './types';

const ProjectParticipation = lazy(() => import('./Collaboration').then(module => ({ default: module.ProjectParticipation })));

export function ProjectDetail() {
    const { projectId } = useParams();
    return <ProjectDetailPage key={projectId} projectId={projectId || ''} />;
}

function ProjectDetailPage({ projectId }: { projectId: string }) {
    const project = useResource<Project>(`/projects/${encodeURIComponent(projectId)}`);
    const me = useResource<Me>('/me');
    const [pending, setPending] = useState(false);
    const submitting = useRef(false);
    const request = useRef<AbortController | null>(null);
    useEffect(() => () => request.current?.abort(), []);
    const [error, setError] = useState('');
    const [archiveOpen, setArchiveOpen] = useState(false);
    const value = project.data;
    const owner = value?.owner.id === me.data?.id;
    const next = value && ({ draft: 'open', open: 'in_progress', in_progress: 'completed' } as Partial<Record<Project['status'], Project['status']>>)[value.status];
    const canPublish = value?.project_type !== 'research_opportunity' || (me.data?.role === 'faculty' && !!me.data.faculty_verified_at);
    async function changeStatus(status: Project['status']) {
        if (submitting.current || !value) return;
        const controller = new AbortController();
        request.current = controller;
        submitting.current = true;
        setPending(true);
        setError('');
        try { await api.patch(`/projects/${value.id}/status`, { status }, controller.signal); if (!controller.signal.aborted) { setArchiveOpen(false); refreshResources(['/me/projects', '/me/teams', '/projects']); project.reload(); } }
        catch (cause) { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Could not update status.'); }
        finally { submitting.current = false; if (!controller.signal.aborted) setPending(false); }
    }
    return <main className="app-page">
        <PageHeading eyebrow={value?.project_type === 'research_opportunity' ? 'Faculty research' : 'Project overview'} title={value?.title || 'Project details'} actions={<Link to="/main">All projects <Icon name="arrow" /></Link>} />
        {me.error && <p role="alert">{me.error.message} <button onClick={me.reload}>Retry account</button></p>}
        {project.loading && <PageLoading>Loading project…</PageLoading>}
        {project.error && <div role="alert">{project.error instanceof ApiError && project.error.status === 404 ? 'Project not found or unavailable to your account.' : project.error.message}<button onClick={project.reload}>Retry project</button></div>}
        {archiveOpen && <ConfirmDialog title="Archive this project?" description="Archiving closes applications and makes the project and its team read-only. You cannot undo this here." confirmLabel="Confirm archive" pending={pending} error={error} cancel={() => setArchiveOpen(false)} confirm={() => void changeStatus('archived')} />}
        {value && <article className="project-detail">
            <nav className="subnav" aria-label="Project navigation"><StatusBadge status={value.status} />{owner && <><Link to={`/projects/${value.id}/team`}>View team</Link><Link to={`/projects/${value.id}/applications`}>Review applications</Link></>}</nav>
            {owner && <section className="management-panel" aria-label="Manage project">
                {value.status === 'draft' && <p>This is your private draft preview. Publish it to make it discoverable.</p>}
                {value.status === 'archived' ? <p>Archived projects are read-only.</p> : <>
                    <Link to={`/projects/${value.id}/edit`}>Edit project <Icon name="arrow" /></Link>
                    <fieldset disabled={pending || project.loading}><legend>Project status</legend>
                        {next && <button className="button-primary" onClick={() => changeStatus(next)} disabled={next === 'open' && !canPublish}>{pending ? 'Updating…' : next === 'open' ? 'Publish project' : next === 'in_progress' ? 'Start project' : 'Complete project'}</button>}
                        <button className="button-danger" onClick={() => { setError(''); setArchiveOpen(true); }}>Archive project</button>
                        <p>Archiving makes this project read-only and cannot be undone here.</p>
                    </fieldset>
                    {next === 'open' && !canPublish && <p>Publishing research requires verified faculty.</p>}
                </>}
                {error && !archiveOpen && <p role="alert">{error}</p>}
            </section>}
            <div className="detail-grid"><div className="detail-content">
                <h2>About the project</h2><p className="project-description">{value.description}</p>
                <h3>Skills</h3>{value.skills.length ? <ul>{value.skills.map(skill => <li key={skill.id}>{skill.name} · {skill.required ? 'Required' : 'Optional'}</li>)}</ul> : <p className="form-note">No skills listed.</p>}
                <h3>Interests</h3>{value.interests.length ? <div className="tag-list">{value.interests.map(item => <span className="tag" key={item.id}>{item.name}</span>)}</div> : <p className="form-note">No interests listed.</p>}
            </div><aside className="detail-sidebar" aria-label="Project information"><dl>
                <dt>Project owner</dt><dd>{value.owner.display_name || 'Project owner'}{value.owner.faculty_verified && <span className="verified-label"> · Verified faculty</span>}</dd>
                <dt>Project type</dt><dd>{value.project_type === 'research_opportunity' ? 'Faculty research' : 'Student project'}</dd>
                <dt>Weekly hours</dt><dd>{value.weekly_hours === null ? 'Unspecified' : `${value.weekly_hours} hours per week`}</dd>
                <dt>Minimum experience</dt><dd>{value.minimum_experience_years === null ? 'Unspecified' : `${value.minimum_experience_years} years`}</dd>
                <dt>Team capacity</dt><dd>{value.member_count} {value.member_count === 1 ? 'member' : 'members'} · {value.max_members === null ? 'No capacity limit set' : `Capacity ${value.max_members}`}</dd>
            </dl></aside></div>
            {me.data && !owner && <Suspense fallback={<PageLoading>Loading application options…</PageLoading>}><ProjectParticipation key={value.id} project={value} /></Suspense>}
        </article>}
    </main>;
}
