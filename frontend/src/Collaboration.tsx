import type { FormEvent, ReactNode } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { AccountAccess } from './AccountAccess';
import { api } from './api';
import { ApiError } from './lib/api-client';
import { useResource } from './use-resource';
import { useMutation } from './use-mutation';
import type { ApplicationRecord, Me, Page, Project, ProjectApplications, Team } from './types';

function PageHeader({ title, children }: { title: string; children?: ReactNode }) {
    return <><header><h1>{title}</h1><nav><Link to="/main">Project Hub</Link> · <Link to="/my-applications">My Applications</Link>{children}</nav></header><AccountAccess /></>;
}

function StatusFilter() {
    const [params, setParams] = useSearchParams();
    return <label>Application status<select value={params.get('status') || ''} onChange={event => setParams(event.target.value ? { status: event.target.value } : {})}>
        <option value="">All statuses</option>
        {['pending','accepted','rejected','withdrawn'].map(status => <option key={status} value={status}>{status}</option>)}
    </select></label>;
}

function Pager({ next }: { next: string | null }) {
    const [params, setParams] = useSearchParams();
    return <nav aria-label="Result pages" className="pagination">
        {params.has('cursor') && <button onClick={() => { const value = new URLSearchParams(params); value.delete('cursor'); setParams(value); }}>First page</button>}
        {next && <button onClick={() => { const value = new URLSearchParams(params); value.set('cursor', next); setParams(value); }}>Next page</button>}
    </nav>;
}

function usePageQuery() {
    const [params] = useSearchParams();
    const query = new URLSearchParams({ limit: '10' });
    for (const name of ['status','cursor']) if (params.get(name)) query.set(name, params.get(name)!);
    return query.toString();
}

export function ProjectParticipation({ project }: { project: Project }) {
    const mine = useResource<Page<ApplicationRecord>>(`/me/applications?project_id=${encodeURIComponent(project.id)}&limit=1`);
    const mutation = useMutation();
    const current = mine.data?.items[0];
    const full = project.max_members !== null && project.member_count >= project.max_members;
    const canSubmit = project.status === 'open' && !full && (!current || current.status === 'withdrawn');
    function apply(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        const message = String(new FormData(event.currentTarget).get('message') || '').trim();
        void mutation.run(signal => api.post(`/projects/${project.id}/applications`, { message: message || null }, signal), mine.reload);
    }
    return <section aria-label="Your project application">
        <h3>Your application</h3>
        {mine.loading && <p role="status">Loading your application…</p>}
        {mine.error && <p role="alert">{mine.error.message} <button onClick={mine.reload}>Retry application</button></p>}
        {mine.data && <>
            {current && <><p>Application status: <strong>{current.status}</strong></p><p className="project-description">{current.message}</p></>}
            {current?.status === 'pending' && <button disabled={mutation.pending} onClick={() => void mutation.run(signal => api.patch(`/applications/${current.id}/withdraw`, {}, signal), mine.reload)}>{mutation.pending ? 'Withdrawing…' : 'Withdraw application'}</button>}
            {current?.status === 'accepted' && <p>Your application was accepted. <Link to={`/projects/${project.id}/team`}>View team</Link>. Leaving or removal ends team access; rejoining is not available yet.</p>}
            {current?.status === 'rejected' && <p>This application was rejected. Resubmission is not available.</p>}
            {canSubmit && <form onSubmit={apply}>
                <fieldset disabled={mutation.pending} className="profile-fields"><legend>{current ? 'Resubmit application' : 'Apply to this project'}</legend>
                    <label>Application message (optional)<textarea name="message" maxLength={2000} rows={3} defaultValue={current?.message || ''} /></label>
                    <p>Your message is visible to you and the project owner.</p>
                    <button type="submit">{mutation.pending ? 'Submitting…' : current ? 'Resubmit application' : 'Apply to project'}</button>
                </fieldset>
            </form>}
            {!canSubmit && (!current || current.status === 'withdrawn') && <p>{project.status !== 'open' ? 'Applications are closed for this project.' : 'This team is full.'}</p>}
        </>}
        {mutation.error && <p role="alert">{mutation.error}</p>}
    </section>;
}

export function MyApplications() {
    const query = usePageQuery();
    const applications = useResource<Page<ApplicationRecord>>(`/me/applications?${query}`);
    const mutation = useMutation();
    return <main className="app-page">
        <PageHeader title="My Applications" />
        <StatusFilter />
        {applications.loading && <p role="status">Loading your applications…</p>}
        {applications.error && <p role="alert">{applications.error.message} <button onClick={applications.reload}>Retry applications</button></p>}
        {applications.data?.items.length === 0 && <p>No applications to show.</p>}
        <div className="project-cards">{applications.data?.items.map(item => <article className="project-card" key={item.id}>
            <h2>{item.project.title}</h2>
            <p>Application status: <strong>{item.status}</strong> · Project: {item.project.status.replaceAll('_',' ')}</p>
            <p className="project-description">{item.message || 'No message included.'}</p>
            <Link to={`/projects/${item.project.id}`}>View project</Link>
            {item.status === 'pending' && <button disabled={mutation.pending} onClick={() => void mutation.run(signal => api.patch(`/applications/${item.id}/withdraw`, {}, signal), applications.reload)}>Withdraw application</button>}
            {item.status === 'withdrawn' && item.project.status === 'open' && <p>Open the project to resubmit if there is space.</p>}
            {item.status === 'rejected' && <p>Rejected applications cannot be resubmitted.</p>}
            {item.status === 'accepted' && <p><Link to={`/projects/${item.project.id}/team`}>View team</Link>. Acceptance stays in your history after leaving or removal; rejoining is not available yet.</p>}
        </article>)}</div>
        <p>Private project details and rosters are available only to their owner and current members.</p>
        {mutation.error && <p role="alert">{mutation.error}</p>}
        {applications.data && <Pager next={applications.data.next_cursor} />}
    </main>;
}

export function ProjectApplicants() {
    const { projectId = '' } = useParams();
    return <ApplicantList key={projectId} projectId={projectId} />;
}

function ApplicantList({ projectId }: { projectId: string }) {
    const query = usePageQuery();
    const applications = useResource<ProjectApplications>(`/projects/${encodeURIComponent(projectId)}/applications?${query}`);
    const mutation = useMutation();
    const projectStatus = applications.data?.project.status;
    function decide(item: ApplicationRecord, status: 'accepted' | 'rejected') {
        void mutation.run(signal => api.patch(`/applications/${item.id}/decision`, { status }, signal), applications.reload);
    }
    return <main className="app-page">
        <PageHeader title="Review applications"><> · <Link to={`/projects/${projectId}`}>Project details</Link> · <Link to={`/projects/${projectId}/team`}>Team</Link></></PageHeader>
        <StatusFilter />
        {applications.loading && <p role="status">Loading applicants…</p>}
        {applications.error && <p role="alert">{applications.error.message} <button onClick={applications.reload}>Retry applicants</button></p>}
        {applications.data && <>
            <h2>{applications.data.project.title}</h2>
            {applications.data.project.status !== 'open' && <p>Acceptance requires an open project. Archived projects are read-only.</p>}
            {applications.data.items.length === 0 && <p>No applications to review.</p>}
            <div className="project-cards">{applications.data.items.map(item => <article className="project-card" key={item.id}>
                <h3>{item.applicant.display_name || 'Applicant'}</h3>
                <p>{item.applicant.role}{item.applicant.faculty_verified ? ' · Verified faculty' : ''} · {item.status}</p>
                <p className="project-description">{item.message || 'No message included.'}</p>
                {item.status === 'pending' && <fieldset disabled={mutation.pending || projectStatus === 'archived'}><legend>Review {item.applicant.display_name || 'applicant'}</legend>
                    <button disabled={projectStatus !== 'open'} onClick={() => decide(item, 'accepted')}>Accept {item.applicant.display_name || 'applicant'}</button>
                    <button onClick={() => decide(item, 'rejected')}>Reject {item.applicant.display_name || 'applicant'}</button>
                </fieldset>}
            </article>)}</div>
            <Pager next={applications.data.next_cursor} />
        </>}
        {mutation.pending && <p role="status">Saving decision…</p>}
        {mutation.error && <p role="alert">{mutation.error}</p>}
    </main>;
}

export function ProjectTeam() {
    const { projectId = '' } = useParams();
    return <TeamList key={projectId} projectId={projectId} />;
}

function TeamList({ projectId }: { projectId: string }) {
    const [params] = useSearchParams();
    const query = new URLSearchParams({ limit: '20' });
    if (params.get('cursor')) query.set('cursor', params.get('cursor')!);
    const roster = useResource<Team>(`/projects/${encodeURIComponent(projectId)}/members?${query}`);
    const me = useResource<Me>('/me');
    const mutation = useMutation();
    const navigate = useNavigate();
    const owner = roster.data?.project.owner_id === me.data?.id;
    const archived = roster.data?.project.status === 'archived';
    function remove(userId: string) {
        void mutation.run(signal => api.delete(`/projects/${projectId}/members/${userId}`, signal), () => {
            if (userId === me.data?.id) navigate('/my-applications'); else roster.reload();
        });
    }
    return <main className="app-page">
        <PageHeader title="Project team"><> · <Link to={`/projects/${projectId}`}>Project details</Link></></PageHeader>
        {roster.loading && <p role="status">Loading team…</p>}
        {roster.error && <p role="alert">{roster.error instanceof ApiError && [403,404].includes(roster.error.status) ? 'The team is unavailable or restricted to the owner and current members.' : roster.error.message} <button onClick={roster.reload}>Retry team</button></p>}
        {me.error && <p role="alert">{me.error.message} <button onClick={me.reload}>Retry account</button></p>}
        {roster.data && <>
            <h2>{roster.data.project.title}</h2>
            <p>{roster.data.member_count} {roster.data.member_count === 1 ? 'member' : 'members'}{roster.data.max_members === null ? ' · No capacity limit' : ` / ${roster.data.max_members} capacity`} · Includes the owner.</p>
            {roster.data.project.status === 'archived' && <p>Archived teams are read-only.</p>}
            <ul className="team-list">{roster.data.items.map(item => <li key={item.user.id}>
                <h3>{item.user.display_name || 'Team member'}{item.is_owner ? ' · Owner' : ''}</h3>
                <p>{item.user.role}{item.user.faculty_verified ? ' · Verified faculty' : ''}</p>
                {!item.is_owner && !archived && (owner || item.user.id === me.data?.id) && <button disabled={mutation.pending} onClick={() => remove(item.user.id)}>{item.user.id === me.data?.id ? 'Leave team' : `Remove ${item.user.display_name || 'member'}`}</button>}
            </li>)}</ul>
            <p>Leaving or removal keeps the application decision as history. It cannot be used to rejoin.</p>
            <Pager next={roster.data.next_cursor} />
        </>}
        {mutation.pending && <p role="status">Updating team…</p>}
        {mutation.error && <p role="alert">{mutation.error}</p>}
    </main>;
}
