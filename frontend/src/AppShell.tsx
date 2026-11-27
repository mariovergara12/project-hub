import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { AccountAccess } from './AccountAccess';
import { useResource } from './use-resource';
import { Brand, Icon, PageLoading } from './ui';
import type { Page, Project } from './types';

const ProjectSearch = lazy(() => import('./ProjectSearch').then(module => ({ default: module.ProjectSearch })));
function Modal({ label, className = '', close, children }: { label: string; className?: string; close: () => void; children: ReactNode }) {
    const dialog = useRef<HTMLDialogElement>(null);
    useEffect(() => {
        const element = dialog.current;
        element?.showModal();
        return () => element?.close();
    }, []);
    return <dialog ref={dialog} className={className} aria-label={label} onCancel={event => { event.preventDefault(); close(); }} onClick={event => { if (event.target === event.currentTarget) close(); }}>{children}</dialog>;
}

function SidebarContent({ compact, toggleCompact, openSearch, navigate }: { compact?: boolean; toggleCompact?: () => void; openSearch: () => void; navigate?: () => void }) {
    const projects = useResource<Page<Project>>('/me/projects?limit=4');
    return <><div className="sidebar-scroll">
        <button className="sidebar-search" onClick={openSearch} aria-label="Quick project search"><Icon name="search" /><span>Quick search…</span><kbd>⌘ K</kbd></button>
        <nav className="sidebar-nav" aria-label="Main navigation">
            <p className="sidebar-section-label">Workspace</p>
            <NavLink to="/main" aria-label="Discover projects" title="Discover projects" onClick={navigate}><Icon name="home" /><span>Discover projects</span></NavLink>
            <NavLink to="/my-projects" aria-label="My projects" title="My projects" onClick={navigate}><Icon name="folder" /><span>My projects</span></NavLink>
            <NavLink to="/my-applications" aria-label="Applications" title="Applications" onClick={navigate}><Icon name="send" /><span>Applications</span></NavLink>
            <p className="sidebar-section-label">Build</p>
            <NavLink to="/projects/new" aria-label="Create a project" title="Create a project" onClick={navigate}><Icon name="plus" /><span>Create a project</span></NavLink>
            <NavLink to="/profile" aria-label="Your profile" title="Your profile" onClick={navigate}><Icon name="user" /><span>Your profile</span></NavLink>
        </nav>
        {!!projects.data?.items.length && <section className="sidebar-projects" aria-label="Projects you own"><p className="sidebar-section-label">Your projects</p>{projects.data.items.map(project => <Link to={`/projects/${project.id}`} key={project.id} onClick={navigate}><span className="sidebar-project-dot" /><span>{project.title}<small>{project.status.replaceAll('_', ' ')}</small></span></Link>)}</section>}
        </div><div className="sidebar-bottom"><AccountAccess />{toggleCompact && <button className="sidebar-collapse" aria-label={compact ? 'Expand sidebar' : 'Collapse sidebar'} onClick={toggleCompact}><Icon name="panel" /><span>Collapse sidebar</span></button>}</div>
    </>;
}

export function AppShell() {
    const { pathname } = useLocation();
    const navigate = useNavigate();
    const [compact, setCompact] = useState(false);
    const [searchOpen, setSearchOpen] = useState(false);
    const [mobileOpen, setMobileOpen] = useState(false);
    useEffect(() => {
        document.title = 'Project Hub · Campus collaboration';
        document.getElementById('page-content')?.focus({ preventScroll: true });
        window.scrollTo(0, 0);
    }, [pathname]);
    useEffect(() => {
        function shortcut(event: globalThis.KeyboardEvent) {
            if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
                event.preventDefault();
                setMobileOpen(false);
                setSearchOpen(value => !value);
            }
        }
        window.addEventListener('keydown', shortcut);
        return () => window.removeEventListener('keydown', shortcut);
    }, []);
    function search(query: string) {
        const params = new URLSearchParams();
        if (query) params.set('q', query);
        navigate(`/main${params.size ? `?${params}` : ''}`);
    }
    function openSearch() { setMobileOpen(false); setSearchOpen(true); }
    const context = pathname === '/main' ? 'Discover projects' : pathname === '/profile' ? 'Your profile' : pathname === '/my-projects' ? 'My projects' : pathname === '/my-applications' ? 'Applications' : pathname === '/projects/new' ? 'Create a project' : 'Project workspace';
    return <div className={`app-shell ${compact ? 'sidebar-is-compact' : ''}`}>
        <a href="#page-content" className="skip-link">Skip to content</a>
        <header className="dashboard-topbar"><div className="dashboard-brand"><Brand /></div><button className="mobile-nav-toggle" aria-label="Open navigation" aria-haspopup="dialog" aria-expanded={mobileOpen} onClick={() => setMobileOpen(true)}><Icon name="menu" /></button><div className="dashboard-breadcrumb"><span>Workspace</span><span aria-hidden="true">/</span><strong>{context}</strong></div><div className="topbar-actions"><Link className="button button-primary" to="/projects/new" aria-label="Create project"><Icon name="plus" /><span>Create project</span></Link><Link className="profile-shortcut" to="/profile" aria-label="Your profile"><Icon name="user" /></Link></div></header>
        <aside className="dashboard-sidebar" aria-label="Workspace sidebar"><SidebarContent compact={compact} toggleCompact={() => setCompact(value => !value)} openSearch={openSearch} /></aside>
        <div className="dashboard-workspace"><div id="page-content" tabIndex={-1}><Suspense fallback={<main className="app-page"><PageLoading /></main>}><Outlet /></Suspense></div><footer className="site-footer"><span>Project Hub · Campus collaboration</span><Link to="/profile">Manage your profile <Icon name="arrow" /></Link></footer></div>
        {mobileOpen && <Modal label="Workspace navigation" className="mobile-navigation-dialog" close={() => setMobileOpen(false)}><div className="mobile-sidebar-header"><Brand /><button aria-label="Close navigation" onClick={() => setMobileOpen(false)}><Icon name="close" /></button></div><SidebarContent openSearch={openSearch} navigate={() => setMobileOpen(false)} /></Modal>}
        {searchOpen && <Modal label="Find a project" className="project-search-dialog" close={() => setSearchOpen(false)}><div className="search-dialog-header"><h2>Find a project</h2><button aria-label="Close project search" onClick={() => setSearchOpen(false)}><Icon name="close" /></button></div><Suspense fallback={<PageLoading>Loading project search…</PageLoading>}><ProjectSearch autoFocus compact onSearch={search} onClose={() => setSearchOpen(false)} /></Suspense></Modal>}
    </div>;
}
