import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import { api } from './api';
import { Link, useParams } from 'react-router-dom';
import { AccountAccess } from './AccountAccess';
import { ApiError } from './lib/api-client';
import { useResource } from './use-resource';
import type { Me, Project } from './types';

const ProjectParticipation = lazy(() => import('./Collaboration').then(module => ({ default: module.ProjectParticipation })));

export function ProjectDetail() {
    const { projectId } = useParams();
    return <ProjectDetailPage key={projectId} projectId={projectId || ''} />;
}

function ProjectDetailPage({ projectId }: { projectId: string }) {
    const project = useResource<Project>(`/projects/${encodeURIComponent(projectId || '')}`);
    const me = useResource<Me>('/me');
    const [pending, setPending] = useState(false);
    const submitting = useRef(false);
    const request = useRef<AbortController | null>(null);
    useEffect(() => () => request.current?.abort(), []);
    const [error, setError] = useState('');
    const value = project.data;
    const next = value && ({ draft: 'open', open: 'in_progress', in_progress: 'completed' } as Partial<Record<Project['status'], Project['status']>>)[value.status];
    const canPublish = value?.project_type !== 'research_opportunity' || (me.data?.role === 'faculty' && !!me.data.faculty_verified_at);
    async function changeStatus(status: Project['status']) {
        if (submitting.current || !value) return;
        const controller = new AbortController();
        request.current = controller;
        submitting.current = true;
        setPending(true);
        setError('');
        try { await api.patch(`/projects/${value.id}/status`, { status }, controller.signal); if (!controller.signal.aborted) project.reload(); }
        catch (cause) { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Could not update status.'); }
        finally { submitting.current = false; if (!controller.signal.aborted) setPending(false); }
    }
    return <main className="app-page">
        <header><h1>Project details</h1><Link to="/main">Back to Project Hub</Link></header>
        <AccountAccess />
        <Link to="/my-projects">My Projects</Link>
        {me.error && <p role="alert">{me.error.message} <button onClick={me.reload}>Retry account</button></p>}
        {project.loading && <p role="status">Loading project…</p>}
        {project.error && <div role="alert">
            {project.error instanceof ApiError && project.error.status === 404
                ? 'Project not found or unavailable to your account.' : project.error.message}
            <button onClick={project.reload}>Retry project</button>
        </div>}
        {value && <article className="project-detail">
            <h2>{value.title}</h2>
            <nav><Link to={`/projects/${value.id}/team`}>View team</Link>{value.owner.id === me.data?.id && <> · <Link to={`/projects/${value.id}/applications`}>Review applications</Link></>}</nav>
            {value.owner.id === me.data?.id && <section aria-label="Manage project">
                {value.status === 'draft' && <p>This is your private draft preview. Publish it to make it discoverable.</p>}
                {value.status === 'archived' ? <p>Archived projects are read-only.</p> : <>
                    <Link to={`/projects/${value.id}/edit`}>Edit project</Link>
                    <fieldset disabled={pending || project.loading}><legend>Project status</legend>
                        {next && <button onClick={() => changeStatus(next)} disabled={next === 'open' && !canPublish}>{pending ? 'Updating…' : next === 'open' ? 'Publish project' : next === 'in_progress' ? 'Start project' : 'Complete project'}</button>}
                        <button onClick={() => changeStatus('archived')}>Archive project</button>
                        <p>Archiving makes this project read-only and cannot be undone here.</p>
                    </fieldset>
                    {next === 'open' && !canPublish && <p>Publishing research requires verified faculty.</p>}
                </>}
                {error && <p role="alert">{error}</p>}
            </section>}
            <p className="project-description">{value.description}</p>
            <dl>
                <dt>Type</dt><dd>{value.project_type.replaceAll('_', ' ')}</dd>
                <dt>Status</dt><dd>{value.status.replaceAll('_', ' ')}</dd>
                <dt>Owner</dt><dd>{value.owner.display_name || 'Project owner'} · {value.owner.role}{value.owner.faculty_verified ? ' · Verified faculty' : ''}</dd>
                <dt>Weekly hours</dt><dd>{value.weekly_hours ?? 'Unspecified'}</dd>
                <dt>Minimum experience (years)</dt><dd>{value.minimum_experience_years ?? 'Unspecified'}</dd>
                <dt>Team</dt><dd>{value.member_count} {value.member_count === 1 ? 'member' : 'members'} · {value.max_members === null ? 'No capacity limit set' : `Capacity ${value.max_members}`}</dd>
            </dl>
            {me.data && value.owner.id !== me.data.id && <Suspense fallback={<p role="status">Loading application options…</p>}><ProjectParticipation key={value.id} project={value} /></Suspense>}
            <h3>Skills</h3>
            {value.skills.length ? <ul>{value.skills.map(skill => <li key={skill.id}>{skill.name} · {skill.required ? 'Required' : 'Optional'}</li>)}</ul> : <p>No skills listed.</p>}
            <h3>Interests</h3>
            {value.interests.length ? <ul>{value.interests.map(item => <li key={item.id}>{item.name}</li>)}</ul> : <p>No interests listed.</p>}
        </article>}
    </main>;
}
