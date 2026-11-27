import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Login } from './Login';
import { AuthProvider } from './AuthProvider';
import { RequireAuth } from './RequireAuth';
import { AppShell } from './AppShell';
import { PageLoading } from './ui';
import './App.css';

const ProjectHub = lazy(() => import('./Coursepage').then(module => ({ default: module.ProjectHub })));
const Profile = lazy(() => import('./Profile').then(module => ({ default: module.Profile })));
const ProjectDetail = lazy(() => import('./ProjectDetail').then(module => ({ default: module.ProjectDetail })));
const ProjectEditor = lazy(() => import('./ProjectEditor').then(module => ({ default: module.ProjectEditor })));
const MyProjects = lazy(() => import('./MyProjects').then(module => ({ default: module.MyProjects })));

const MyApplications = lazy(() => import('./Collaboration').then(module => ({ default: module.MyApplications })));
const ProjectApplicants = lazy(() => import('./Collaboration').then(module => ({ default: module.ProjectApplicants })));
const ProjectTeam = lazy(() => import('./Collaboration').then(module => ({ default: module.ProjectTeam })));

function App() {
    return (
        <AuthProvider>
            <BrowserRouter>
                <Suspense fallback={<PageLoading />}>
                    <Routes>
                        <Route path='/' element={<Login/>}/>
                        <Route element={<RequireAuth/>}>
                          <Route element={<AppShell/>}>
                            <Route path='/main' element={<ProjectHub/>}/>
                            <Route path='/profile' element={<Profile/>}/>
                            <Route path='/my-applications' element={<MyApplications/>}/>
                            <Route path='/projects/:projectId/applications' element={<ProjectApplicants/>}/>
                            <Route path='/projects/:projectId/team' element={<ProjectTeam/>}/>
                            <Route path='/my-projects' element={<MyProjects/>}/>
                            <Route path='/projects/new' element={<ProjectEditor/>}/>
                            <Route path='/projects/:projectId/edit' element={<ProjectEditor/>}/>
                            <Route path='/projects/:projectId' element={<ProjectDetail/>}/>
                          </Route>
                        </Route>
                    </Routes>
                </Suspense>
            </BrowserRouter>
        </AuthProvider>
    );
}

export default App;
