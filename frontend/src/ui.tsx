import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import type { Project } from './types';

export type IconName = 'arrow' | 'plus' | 'search' | 'filter' | 'grid' | 'folder' | 'send' | 'user' | 'clock' | 'team' | 'check' | 'logout' | 'home' | 'panel' | 'menu' | 'close';
const paths: Record<IconName, ReactNode> = {
    home: <><path d="m3 10 9-7 9 7M5 9v12h14V9M9 21v-7h6v7" /></>,
    panel: <><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M9 4v16" /></>,
    menu: <path d="M4 6h16M4 12h16M4 18h16" />,
    close: <path d="m6 6 12 12M18 6 6 18" />,
    arrow: <><path d="M5 12h14M13 6l6 6-6 6" /></>,
    plus: <path d="M12 5v14M5 12h14" />,
    search: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 4 4" /></>,
    filter: <><path d="M4 7h16M4 17h16" /><circle cx="9" cy="7" r="2" /><circle cx="15" cy="17" r="2" /></>,
    grid: <><rect x="4" y="4" width="6" height="6" /><rect x="14" y="4" width="6" height="6" /><rect x="4" y="14" width="6" height="6" /><rect x="14" y="14" width="6" height="6" /></>,
    folder: <path d="M3 6h7l2 3h9v11H3z" />,
    send: <><path d="m3 10 18-7-7 18-3-8-8-3ZM11 13 21 3" /></>,
    user: <><circle cx="12" cy="8" r="4" /><path d="M4 21v-2a8 8 0 0 1 16 0v2" /></>,
    clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
    team: <><circle cx="9" cy="8" r="3" /><path d="M3 20v-2a6 6 0 0 1 12 0v2M16 5a3 3 0 0 1 0 6M18 14a5 5 0 0 1 3 4v2" /></>,
    check: <path d="m5 12 4 4L19 6" />,
    logout: <><path d="M9 4H4v16h5M10 12h11m-4-4 4 4-4 4" /></>,
};

export function Icon({ name, className = '' }: { name: IconName; className?: string }) {
    return <svg className={`icon ${className}`} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">{paths[name]}</svg>;
}

export function Brand({ linked = true }: { linked?: boolean }) {
    const content = <><span className="brand-mark" aria-hidden="true"><span /><span /><span /></span><span>Project Hub<span className="brand-period">.</span></span></>;
    return linked ? <Link className="brand" to="/main" aria-label="Project Hub home">{content}</Link> : <span className="brand">{content}</span>;
}

export function PageHeading({ title, description, eyebrow, actions }: { title: string; description?: string; eyebrow?: string; actions?: ReactNode }) {
    return <header className="page-heading"><div>{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h1>{title}</h1>{description && <p className="page-description">{description}</p>}</div>{actions && <div className="heading-actions">{actions}</div>}</header>;
}

const labels: Record<string, string> = { in_progress: 'In progress', research_opportunity: 'Faculty research', student_project: 'Student project' };
export function StatusBadge({ status }: { status: string }) {
    return <span className={`status-badge status-${status}`}><span aria-hidden="true" />{labels[status] || status}</span>;
}

export function PageLoading({ children = 'Loading page…' }: { children?: ReactNode }) {
    return <p className="loading-message" role="status"><span className="loading-indicator" aria-hidden="true" />{children}</p>;
}

export function EmptyState({ title, description, children }: { title: string; description: string; children?: ReactNode }) {
    return <div className="empty-state"><Icon name="folder" /><h2>{title}</h2><p>{description}</p>{children}</div>;
}

export function ProjectCard({ project, editable = false, children }: { project: Project; editable?: boolean; children?: ReactNode }) {
    return <article className="project-card">
        <div className="card-topline"><span className="project-type">{labels[project.project_type]}</span><StatusBadge status={project.status} /></div>
        <h2><Link to={`/projects/${project.id}`}>{project.title}</Link></h2>
        <p className="card-description">{project.description}</p>
        <div className="tag-list">{project.skills.slice(0, 3).map(skill => <span className="tag" key={skill.id}>{skill.name}</span>)}{project.skills.length > 3 && <span className="tag">+{project.skills.length - 3} more</span>}</div>
        <p className="card-owner">{project.owner.display_name || 'Project owner'}{project.owner.faculty_verified && <span className="verified-label"><Icon name="check" />Verified faculty</span>}</p>
        <div className="card-facts"><span><Icon name="clock" />{project.weekly_hours === null ? 'Hours not specified' : `${project.weekly_hours} hrs / week`}</span><span><Icon name="team" />{project.member_count}{project.max_members === null ? ' members' : ` / ${project.max_members} members`}</span></div>
        <div className="card-actions"><Link to={`/projects/${project.id}`}>View project <Icon name="arrow" /></Link>{editable && project.status !== 'archived' && <Link to={`/projects/${project.id}/edit`}>Edit project</Link>}{children}</div>
    </article>;
}

export function CollaborationArt() {
    return <div className="collaboration-art" aria-hidden="true"><div className="art-orbit orbit-one" /><div className="art-orbit orbit-two" /><div className="art-orbit orbit-three" /><div className="art-core"><span className="brand-mark"><span /><span /><span /></span></div><span className="art-node node-one">Design</span><span className="art-node node-two">Research</span><span className="art-node node-three">Engineering</span><span className="art-coordinate">IDEAS × PEOPLE</span></div>;
}
