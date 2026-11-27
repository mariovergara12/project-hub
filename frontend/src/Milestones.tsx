import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { api } from './api';
import { ApiError } from './lib/api-client';
import { ConfirmDialog } from './ConfirmDialog';
import { EmptyState, Icon, PageHeading, PageLoading, StatusBadge } from './ui';
import { useMutation } from './use-mutation';
import { useResource } from './use-resource';
import type { Milestone, MilestonePage, MilestoneStatus } from './types';

const statuses: { value: MilestoneStatus; label: string }[] = [
    { value: 'todo', label: 'To do' }, { value: 'in_progress', label: 'In progress' }, { value: 'completed', label: 'Completed' },
];

function MilestoneForm({ projectId, initial, cancel, saved }: {
    projectId: string; initial?: Milestone; cancel: () => void; saved: () => void;
}) {
    const mutation = useMutation();
    function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        const values = new FormData(event.currentTarget);
        const body = {
            title: String(values.get('title') || '').trim(),
            description: String(values.get('description') || '').trim() || null,
            due_date: String(values.get('due_date') || '') || null,
            status: String(values.get('status') || 'todo'),
        };
        void mutation.run(signal => initial
            ? api.patch(`/milestones/${initial.id}`, body, signal)
            : api.post(`/projects/${projectId}/milestones`, body, signal), saved);
    }
    return <section className="milestone-editor" aria-label={initial ? 'Edit milestone' : 'New milestone'}>
        <h2>{initial ? 'Edit milestone' : 'Add a milestone'}</h2>
        <form onSubmit={submit} aria-busy={mutation.pending}>
            <fieldset className="profile-fields" disabled={mutation.pending}><legend>Milestone details</legend>
                <label className="field-wide">Title<input name="title" required maxLength={200} defaultValue={initial?.title || ''} autoFocus /></label>
                <label className="field-wide">Description (optional)<textarea name="description" maxLength={10000} rows={3} defaultValue={initial?.description || ''} /></label>
                <label>Due date (optional)<input name="due_date" type="date" min="0001-01-01" max="9999-12-31" defaultValue={initial?.due_date || ''} /></label>
                <label>Status<select name="status" defaultValue={initial?.status || 'todo'}>{statuses.map(status => <option key={status.value} value={status.value}>{status.label}</option>)}</select></label>
                <div className="field-wide milestone-form-actions"><button className="button-primary" type="submit">{mutation.pending ? 'Saving…' : initial ? 'Save milestone' : 'Create milestone'}</button><button type="button" onClick={cancel}>Cancel</button></div>
            </fieldset>
            {mutation.error && <p role="alert">{mutation.error}</p>}
        </form>
    </section>;
}

function DeleteMilestoneDialog({ milestone, cancel, deleted }: { milestone: Milestone; cancel: () => void; deleted: () => void }) {
    const mutation = useMutation();
    return <ConfirmDialog title={`Delete “${milestone.title}”?`} description="This permanently removes the milestone and its progress. This cannot be undone."
        confirmLabel="Delete milestone" pending={mutation.pending} error={mutation.error} cancel={cancel}
        confirm={() => void mutation.run(signal => api.delete(`/milestones/${milestone.id}`, signal), deleted)} />;
}

function dueLabel(date: string) {
    // A due date is a calendar day, not a UTC timestamp.
    return new Date(`${date}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

export function ProjectMilestones() {
    const { projectId = '' } = useParams();
    return <MilestoneWorkspace key={projectId} projectId={projectId} />;
}

function MilestoneWorkspace({ projectId }: { projectId: string }) {
    const [params, setParams] = useSearchParams();
    const query = new URLSearchParams({ limit: '12' });
    for (const name of ['status', 'cursor']) if (params.get(name)) query.set(name, params.get(name)!);
    const resource = useResource<MilestonePage>(`/projects/${encodeURIComponent(projectId)}/milestones?${query}`);
    const mutation = useMutation();
    const [editor, setEditor] = useState<{ initial?: Milestone } | null>(null);
    const [removal, setRemoval] = useState<Milestone | null>(null);
    const [message, setMessage] = useState('');
    const data = resource.data;
    const editable = !!data && !['completed', 'archived'].includes(data.project.status);
    const blocked = mutation.pending || !!editor;
    const total = data?.progress.total || 0;
    const completed = data?.progress.completed || 0;
    const now = new Date();
    const today = `${now.getFullYear().toString().padStart(4, '0')}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    function saved(text: string) { setMessage(text); resource.reload(); }
    function page(cursor?: string) {
        const next = new URLSearchParams(params);
        if (cursor) next.set('cursor', cursor); else next.delete('cursor');
        setParams(next);
    }
    return <main className="app-page">
        <PageHeading eyebrow="Project workspace" title="Milestones" description="Turn your project into clear next steps, and keep your team moving together."
            actions={editable && <button className="button-primary" disabled={blocked} onClick={() => { setMessage(''); setEditor({}); }}><Icon name="plus" />Add milestone</button>} />
        <nav className="subnav" aria-label="Project navigation"><Link to={`/projects/${projectId}`}>Project details</Link><Link to={`/projects/${projectId}/team`}>Team</Link><Link to="/my-teams">My teams</Link></nav>
        {message && <p role="status">{message}</p>}
        {resource.loading && <PageLoading>Loading milestones…</PageLoading>}
        {resource.error && <p role="alert">{resource.error instanceof ApiError && [403, 404].includes(resource.error.status) ? 'Milestones are available only to the project owner and current team members.' : resource.error.message} <button onClick={resource.reload}>Retry milestones</button></p>}
        {data && <>
            <h2 className="milestone-project-title">{data.project.title}</h2>
            <section className="milestone-progress" aria-label="Overall project progress">
                <div className="milestone-progress-heading"><div><h3>Overall progress</h3><p>{completed} of {total} milestones completed</p></div><strong>{total ? Math.round(completed / total * 100) : 0}%</strong></div>
                <progress aria-label="Milestones completed" max={total || 1} value={completed} />
                <dl className="milestone-counts"><div><dt>To do</dt><dd>{data.progress.todo}</dd></div><div><dt>In progress</dt><dd>{data.progress.in_progress}</dd></div><div><dt>Completed</dt><dd>{completed}</dd></div></dl>
            </section>
            {!editable && <p className="milestone-readonly">This project is {data.project.status}. Milestones are read-only.</p>}
            {editable && editor && <MilestoneForm key={editor.initial?.id || 'new'} projectId={projectId} initial={editor.initial} cancel={() => setEditor(null)} saved={() => { setEditor(null); saved(editor.initial ? 'Milestone saved.' : 'Milestone created.'); }} />}
            <div className="list-toolbar"><label>Milestone status<select disabled={blocked} value={params.get('status') || ''} onChange={event => setParams(event.target.value ? { status: event.target.value } : {})}>
                <option value="">All statuses</option>{statuses.map(status => <option key={status.value} value={status.value}>{status.label}</option>)}
            </select></label><span className="section-note">Progress includes all milestones.</span></div>
            {data.items.length === 0 && <EmptyState title={params.has('status') || params.has('cursor') ? 'No milestones on this page' : 'Start with a clear next step'} description={params.has('status') || params.has('cursor') ? 'Try another status or return to the first page.' : editable ? 'Add your first milestone to give your team a shared plan.' : 'This project has no milestones.'} />}
            <ul className="milestone-list">{data.items.map(item => {
                const overdue = item.status !== 'completed' && !!item.due_date && item.due_date < today;
                return <li className="milestone-item" key={item.id}>
                    <div className="milestone-item-content"><h3>{item.title}</h3><p className="project-description">{item.description || 'No description added.'}</p>
                        <p className={overdue ? 'milestone-overdue' : 'milestone-due'}>{item.due_date ? <><time dateTime={item.due_date}>Due {dueLabel(item.due_date)}</time>{overdue && ' · Overdue'}</> : 'No due date'}</p></div>
                    <div className="milestone-item-actions">{editable ? <>
                        <label className="sr-only" htmlFor={`status-${item.id}`}>Status for {item.title}</label><select id={`status-${item.id}`} value={item.status} disabled={blocked} onChange={event => void mutation.run(signal => api.patch(`/milestones/${item.id}`, { status: event.target.value }, signal), () => saved('Milestone status updated.'))}>{statuses.map(status => <option key={status.value} value={status.value}>{status.label}</option>)}</select>
                        <button disabled={blocked} aria-label={`Edit ${item.title}`} onClick={() => { setMessage(''); setEditor({ initial: item }); }}>Edit</button>
                        <button className="button-danger" disabled={blocked} aria-label={`Delete ${item.title}`} onClick={() => setRemoval(item)}>Delete</button>
                    </> : <StatusBadge status={item.status} />}</div>
                </li>;
            })}</ul>
            <nav className="pagination" aria-label="Milestone pages">{params.has('cursor') && <button disabled={blocked} onClick={() => page()}>First page</button>}{data.next_cursor && <button disabled={blocked} onClick={() => page(data.next_cursor!)}>Next page</button>}</nav>
        </>}
        {removal && <DeleteMilestoneDialog milestone={removal} cancel={() => setRemoval(null)} deleted={() => { setRemoval(null); saved('Milestone deleted.'); }} />}
        {mutation.error && <p role="alert">{mutation.error} <button onClick={resource.reload}>Refresh milestones</button></p>}
    </main>;
}
