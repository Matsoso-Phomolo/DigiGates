// @vitest-environment jsdom
import React,{act} from 'react';
import {createRoot} from 'react-dom/client';
import {MemoryRouter} from 'react-router-dom';
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest';
import App from './App.jsx';

const account=(role,approval_status='ACTIVE',is_active=true)=>({user_id:1,full_name:'Verified User',email:'verified@example.com',role,approval_status,gender:null,date_of_birth:null,is_active,created_at:'2026-01-01T00:00:00',updated_at:'2026-01-01T00:00:00'});
const response=value=>Promise.resolve({ok:true,status:200,json:()=>Promise.resolve(value)});
const emptyPage={items:[],page:1,page_size:10,total:0,pages:1};

describe('verified application session navigation',()=>{
  let container; let root;
  beforeEach(()=>{globalThis.IS_REACT_ACT_ENVIRONMENT=true;container=document.createElement('div');document.body.appendChild(container);root=createRoot(container)});
  afterEach(()=>{act(()=>root.unmount());container.remove();localStorage.clear();vi.restoreAllMocks()});

  async function renderWithBackendUser(user,cached=account('SUPER_ADMIN'),path='/profile'){
    localStorage.setItem('dg_token','test-token');localStorage.setItem('dg_user',JSON.stringify(cached));
    global.fetch=vi.fn(url=>String(url).endsWith('/profile')?response(user):response(String(url).includes('admin-requests')?[]:emptyPage));
    await act(async()=>{root.render(<MemoryRouter initialEntries={[path]}><App/></MemoryRouter>);await new Promise(resolve=>setTimeout(resolve,0))});
  }

  const coreLinks=()=>Object.fromEntries([...container.querySelectorAll('.workspaceMenu nav a')].map(link=>[link.textContent.trim().toLowerCase(),link.getAttribute('href')]));

  it('preserves educational navigation for an active Learner',async()=>{
    await renderWithBackendUser(account('LEARNER'));
    expect(coreLinks()).toEqual({learn:'/learn',explore:'/explore',build:'/build'});
    expect(container.querySelector('.profileTrigger')?.getAttribute('href')).toBe('/profile');
    expect(container.querySelector('.profileTrigger')?.textContent).toContain('Verified User');
  });

  it('shows only role-appropriate navigation for an approved Admin',async()=>{
    await renderWithBackendUser(account('ADMIN'),account('ADMIN'),'/admin?section=learners');
    expect(coreLinks()).toEqual({learners:'/admin?section=learners'});
    expect(container.querySelector('.workspaceMenu nav a.active')?.textContent).toContain('Learners');
    expect(container.querySelector('.side button.active')?.textContent).toBe('Learners');
    expect(container.querySelector('.workspaceActions').children).toHaveLength(4);
  });

  it('shows all three role-appropriate destinations for an active Super Admin',async()=>{
    await renderWithBackendUser(account('SUPER_ADMIN'),account('SUPER_ADMIN'),'/super-admin?section=requests');
    expect(coreLinks()).toEqual({'admin requests':'/super-admin?section=requests',learners:'/super-admin?section=learners',administrators:'/super-admin?section=admins'});
    expect(container.querySelector('.workspaceMenu nav a.active')?.textContent).toContain('Admin Requests');
    expect(container.querySelector('.side button.active')?.textContent).toBe('Admin Requests');
    expect(container.querySelector('.workspaceActions').children).toHaveLength(4);
  });

  it('marks the current Super Admin section active in both header and sidebar',async()=>{
    await renderWithBackendUser(account('SUPER_ADMIN'),account('SUPER_ADMIN'),'/super-admin?section=requests');
    expect(container.querySelector('.workspaceMenu nav a.active')?.textContent).toContain('Admin Requests');
    expect(container.querySelector('.workspaceMenu nav a.active')?.getAttribute('aria-current')).toBe('page');
    expect(container.querySelector('.side button.active')?.textContent).toBe('Admin Requests');
  });

  it.each(['ADMIN','SUPER_ADMIN'])('does not grant %s access to Learner routes',async role=>{
    await renderWithBackendUser(account(role),account(role),'/learn');
    expect(container.textContent).not.toContain('LEARN • OPERATOR');
    expect(coreLinks()).not.toHaveProperty('learn');
  });

  it.each(['PENDING','REJECTED'])('does not expose learning or administrative navigation to a %s Admin',async status=>{
    await renderWithBackendUser(account('ADMIN',status));
    expect(coreLinks()).toEqual({});
    expect(container.querySelector('.roleDashboardLink')).toBeNull();
  });

  it('provides an accessible collapsible navigation menu',async()=>{
    await renderWithBackendUser(account('LEARNER'));
    const toggle=container.querySelector('.workspaceMenuToggle');
    expect(toggle.getAttribute('aria-controls')).toBe('workspace-navigation');
    expect(toggle.getAttribute('aria-expanded')).toBe('false');
    await act(async()=>{toggle.dispatchEvent(new MouseEvent('click',{bubbles:true}));await Promise.resolve()});
    expect(toggle.getAttribute('aria-expanded')).toBe('true');
    expect(container.querySelector('#workspace-navigation').classList.contains('open')).toBe(true);
  });

  it('uses the backend profile rather than editable cached role data',async()=>{
    await renderWithBackendUser(account('LEARNER'));
    expect(container.querySelector('.roleDashboardLink')).toBeNull();
    expect(container.textContent).toContain('LEARNER');
  });

  it('removes privileged navigation when the verified user logs out',async()=>{
    await renderWithBackendUser(account('SUPER_ADMIN'));
    expect(container.querySelector('.roleDashboardLink')?.getAttribute('href')).toBe('/super-admin?section=requests');
    const logout=container.querySelector('button[title="Sign out"]');
    await act(async()=>{logout.dispatchEvent(new MouseEvent('click',{bubbles:true}));await Promise.resolve()});
    expect(container.querySelector('.roleDashboardLink')).toBeNull();
    expect(localStorage.getItem('dg_token')).toBeNull();
  });
});

describe('authentication dialog accessibility',()=>{
  let container; let root;
  beforeEach(()=>{container=document.createElement('div');document.body.appendChild(container);root=createRoot(container)});
  afterEach(()=>{act(()=>root.unmount());container.remove();localStorage.clear();document.body.style.overflow='';vi.restoreAllMocks()});

  async function renderAt(path){await act(async()=>{root.render(<MemoryRouter initialEntries={[path]}><App/></MemoryRouter>);await Promise.resolve()})}

  it('keeps the complete registration form inside a labelled scrollable dialog',async()=>{
    await renderAt('/signup');
    const dialog=container.querySelector('[role="dialog"]'),form=dialog.querySelector('form');
    expect(dialog.getAttribute('aria-modal')).toBe('true');
    expect(dialog.getAttribute('aria-labelledby')).toBe('auth-dialog-title');
    expect(form.textContent).toContain('Full Name');
    expect(form.textContent).toContain('Account type');
    expect(form.textContent).toContain('Email Address');
    expect(form.textContent).toContain('Password');
    expect(form.textContent).toContain('Submit Registration');
    expect(dialog.querySelector('.close').closest('form')).toBeNull();
    expect(document.body.style.overflow).toBe('hidden');
    expect(document.activeElement).toBe(form.querySelector('input'));
  });

  it('applies the same dialog semantics to Sign In',async()=>{
    await renderAt('/signin');
    const dialog=container.querySelector('[role="dialog"]');
    expect(dialog).not.toBeNull();
    expect(dialog.textContent).toContain('Sign In');
    expect(dialog.querySelector('input[type="email"]')).not.toBeNull();
    expect(dialog.querySelector('input[type="password"]')).not.toBeNull();
  });

  it('closes on Escape and restores background scrolling',async()=>{
    await renderAt('/signup');
    expect(document.body.style.overflow).toBe('hidden');
    await act(async()=>{document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));await Promise.resolve()});
    expect(container.querySelector('[role="dialog"]')).toBeNull();
    expect(document.body.style.overflow).toBe('');
  });
});
