import { Link, useParams } from 'react-router-dom';
import { AccountAccess } from './AccountAccess';
import { ApiError } from './lib/api-client';
import { useResource } from './use-resource';
import type { Project } from './types';

export function ProjectDetail() {
    const { projectId } = useParams();
    const project = useResource<Project>(`/projects/${encodeURIComponent(projectId || '')}`);
    const value = project.data;
    return <main className="app-page">
        <header><h1>Project details</h1><Link to="/main">Back to Project Hub</Link></header>
        <AccountAccess />
        {project.loading && <p role="status">Loading project…</p>}
        {project.error && <div role="alert">
            {project.error instanceof ApiError && project.error.status === 404
                ? 'Project not found or unavailable to your account.' : project.error.message}
            <button onClick={project.reload}>Retry project</button>
        </div>}
        {value && <article className="project-detail">
            <h2>{value.title}</h2>
            <p className="project-description">{value.description}</p>
            <dl>
                <dt>Type</dt><dd>{value.project_type.replaceAll('_', ' ')}</dd>
                <dt>Status</dt><dd>{value.status.replaceAll('_', ' ')}</dd>
                <dt>Owner</dt><dd>{value.owner.display_name || 'Project owner'} · {value.owner.role}{value.owner.faculty_verified ? ' · Verified faculty' : ''}</dd>
                <dt>Weekly hours</dt><dd>{value.weekly_hours ?? 'Unspecified'}</dd>
                <dt>Minimum experience (years)</dt><dd>{value.minimum_experience_years ?? 'Unspecified'}</dd>
                <dt>Team</dt><dd>{value.member_count} members · {value.max_members === null ? 'No capacity limit set' : `Capacity ${value.max_members}`}</dd>
            </dl>
            <h3>Skills</h3>
            {value.skills.length ? <ul>{value.skills.map(skill => <li key={skill.id}>{skill.name} · {skill.required ? 'Required' : 'Optional'}</li>)}</ul> : <p>No skills listed.</p>}
            <h3>Interests</h3>
            {value.interests.length ? <ul>{value.interests.map(item => <li key={item.id}>{item.name}</li>)}</ul> : <p>No interests listed.</p>}
        </article>}
    </main>;
}
