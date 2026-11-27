import { useEffect, useId, useRef, useState } from 'react';
import type { FormEvent, KeyboardEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useResource } from './use-resource';
import { Icon } from './ui';
import type { Page, Project } from './types';

type Props = { initialQuery?: string; onSearch: (query: string) => void; onClose?: () => void; autoFocus?: boolean; compact?: boolean };

export function ProjectSearch({ initialQuery = '', onSearch, onClose, autoFocus = false, compact = false }: Props) {
    const [query, setQuery] = useState(initialQuery);
    const [debouncedQuery, setDebouncedQuery] = useState(initialQuery.trim());
    const [expanded, setExpanded] = useState(autoFocus);
    const [focused, setFocused] = useState(autoFocus);
    const [activeId, setActiveId] = useState<string | null>(null);
    const [exampleIndex, setExampleIndex] = useState(0);
    const root = useRef<HTMLDivElement>(null);
    const input = useRef<HTMLInputElement>(null);
    const listId = useId();
    const navigate = useNavigate();
    useEffect(() => {
        const timer = window.setTimeout(() => setDebouncedQuery(query.trim()), 200);
        return () => window.clearTimeout(timer);
    }, [query]);
    const params = new URLSearchParams({ limit: '20' });
    if (debouncedQuery) params.set('q', debouncedQuery);
    const projects = useResource<Page<Project>>(`/projects?${params}`);
    const waiting = query.trim() !== debouncedQuery || projects.loading;
    const items = waiting ? [] : projects.data?.items || [];
    const activeProject = items.find(project => project.id === activeId);
    const examples = projects.data?.items;
    useEffect(() => {
        if (focused || query || !examples?.length || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return;
        const timer = window.setInterval(() => setExampleIndex(index => (index + 1) % examples.length), 3600);
        return () => window.clearInterval(timer);
    }, [focused, query, examples]);
    useEffect(() => {
        if (!expanded) return;
        function outside(event: PointerEvent) {
            if (root.current && !root.current.contains(event.target as Node)) setExpanded(false);
        }
        document.addEventListener('pointerdown', outside);
        return () => document.removeEventListener('pointerdown', outside);
    }, [expanded]);
    useEffect(() => {
        if (expanded && activeId) document.getElementById(`${listId}-${activeId}`)?.scrollIntoView?.({ block: 'nearest' });
    }, [activeId, expanded, listId]);
    function showAll() {
        setExpanded(false);
        onSearch(query.trim());
        onClose?.();
    }
    function choose(project: Project) {
        setExpanded(false);
        navigate(`/projects/${project.id}`);
        onClose?.();
    }
    function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (expanded && activeProject) choose(activeProject); else showAll();
    }
    function keyboard(event: KeyboardEvent<HTMLInputElement>) {
        if (event.key === 'Escape') {
            event.preventDefault();
            event.stopPropagation();
            setExpanded(false);
            onClose?.();
        } else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
            event.preventDefault();
            setExpanded(true);
            if (!items.length) return;
            const index = items.findIndex(project => project.id === activeId);
            const next = event.key === 'ArrowDown' ? (index + 1) % items.length : index <= 0 ? items.length - 1 : index - 1;
            setActiveId(items[next].id);
        }
    }
    const example = !focused && !query && examples?.length ? examples[exampleIndex % examples.length] : null;
    return <div ref={root} className={`project-search ${compact ? 'project-search-compact' : ''}`}>
        <form className="project-search-form" onSubmit={submit} role="search" aria-label="Find a project">
            <Icon name="search" />
            <div className="project-search-input">
                <input ref={input} autoFocus={autoFocus} role="combobox" aria-label="Search projects" aria-autocomplete="list" aria-expanded={expanded} aria-controls={expanded ? listId : undefined} aria-activedescendant={expanded && activeProject ? `${listId}-${activeProject.id}` : undefined} autoComplete="off" maxLength={200} placeholder={example ? '' : 'Search projects by title or description'} value={query}
                    onChange={event => { setQuery(event.target.value); setActiveId(null); setExpanded(true); }}
                    onFocus={() => { setFocused(true); setExpanded(true); }} onBlur={() => setFocused(false)} onKeyDown={keyboard} />
                {example && <span className="search-rotator" aria-hidden="true">Search for <span key={example.id} className="rotating-project">{example.title}</span></span>}
            </div>
            {!compact && <span className="search-keyboard-hint" aria-hidden="true"><kbd>⌘</kbd><kbd>K</kbd></span>}
            <button type="button" className="search-submit" aria-label="Search all projects" onClick={showAll}><Icon name="arrow" /></button>
        </form>
        {expanded && <div className="project-search-popover">
            <div className="search-results-heading">{debouncedQuery ? 'Matching projects' : 'Explore projects'}<span>↑ ↓ to navigate</span></div>
            {waiting && <p className="search-feedback" role="status">Finding projects…</p>}
            {!waiting && projects.error && <div className="search-feedback" role="alert">Could not load projects. <button type="button" onClick={projects.reload}>Retry search</button></div>}
            <div className="search-results-list" id={listId} role="listbox" aria-label="Project suggestions" aria-busy={waiting}>
                {items.map(project => <Link to={`/projects/${project.id}`} role="option" id={`${listId}-${project.id}`} aria-selected={activeId === project.id} key={project.id} className="search-result" onClick={event => { event.preventDefault(); choose(project); }}>
                    <span className="search-result-icon"><Icon name="folder" /></span><span className="search-result-copy"><strong>{project.title}</strong><span>{project.owner.display_name || 'Project owner'} · {project.project_type === 'research_opportunity' ? 'Faculty research' : 'Student project'}</span></span><Icon name="arrow" />
                </Link>)}
            </div>
            {!waiting && !projects.error && !items.length && <p className="search-feedback">No matching projects. Try a different title or keyword.</p>}
            <button type="button" className="search-all-results" onClick={showAll}>{projects.data?.next_cursor ? 'Browse all matching projects' : 'Show results on the page'}<Icon name="arrow" /></button>
        </div>}
    </div>;
}
