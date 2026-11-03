// @vitest-environment jsdom
import React,{act} from 'react';
import {createRoot} from 'react-dom/client';
import {MemoryRouter} from 'react-router-dom';
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest';
import {ProfileV2,SuperAdminPortal} from './AccountManagement.jsx';

const page={items:[],page:1,page_size:10,total:0,pages:1};
const ok=value=>Promise.resolve({ok:true,status:200,json:()=>Promise.resolve(value)});
const click=element=>act(async()=>{element.dispatchEvent(new MouseEvent('click',{bubbles:true}));await Promise.resolve()});

describe('Super Admin account lists',()=>{
  let container; let root;
  beforeEach(()=>{
    localStorage.setItem('dg_token','test-token');
    container=document.createElement('div');document.body.appendChild(container);root=createRoot(container);
  });
  afterEach(()=>{act(()=>root.unmount());container.remove();localStorage.clear();vi.restoreAllMocks()});

  it('fetches the correct list whenever the role tab changes',async()=>{
    global.fetch=vi.fn((url)=>ok(url.includes('admin-requests')?[]:page));
    await act(async()=>{root.render(<MemoryRouter initialEntries={['/super-admin?section=requests']}><SuperAdminPortal/></MemoryRouter>);await Promise.resolve()});
    const button=label=>[...container.querySelectorAll('button')].find(x=>x.textContent===label);
    await click(button('Learners'));
    expect(container.querySelector('.side button.active')?.textContent).toBe('Learners');
    await click(button('Administrators'));
    expect(container.querySelector('.side button.active')?.textContent).toBe('Administrators');
    expect(fetch.mock.calls.some(([url])=>url.includes('/admin/learners?page=1&page_size=10&q='))).toBe(true);
    expect(fetch.mock.calls.some(([url])=>url.includes('/super-admin/admins?page=1&page_size=10&q='))).toBe(true);
  });

  it('does not describe a failed request as an empty account list',async()=>{
    global.fetch=vi.fn((url)=>url.includes('admin-requests')?ok([]):Promise.reject(new TypeError('Failed to fetch')));
    await act(async()=>{root.render(<MemoryRouter initialEntries={['/super-admin?section=requests']}><SuperAdminPortal/></MemoryRouter>);await Promise.resolve()});
    const learners=[...container.querySelectorAll('button')].find(x=>x.textContent==='Learners');
    await click(learners);
    expect(container.textContent).toContain('Failed to fetch');
    expect(container.textContent).toContain('Unable to load accounts.');
    expect(container.textContent).not.toContain('No accounts match this search.');
  });
});

describe('Profile role navigation',()=>{
  let container; let root;
  const account=(role,approval_status='ACTIVE')=>({user_id:1,full_name:'Role User',email:'role@example.com',role,approval_status,gender:null,date_of_birth:null,is_active:true});
  const renderProfile=user=>act(async()=>{root.render(<MemoryRouter><ProfileV2 user={user} onUserChange={()=>{}} logout={()=>{}}/></MemoryRouter>);await Promise.resolve()});
  beforeEach(()=>{container=document.createElement('div');document.body.appendChild(container);root=createRoot(container)});
  afterEach(()=>{act(()=>root.unmount());container.remove()});

  it('links an active Super Admin to the Super Admin dashboard',async()=>{
    await renderProfile(account('SUPER_ADMIN'));
    const link=[...container.querySelectorAll('a')].find(x=>x.textContent.includes('Super Admin Dashboard'));
    expect(link?.getAttribute('href')).toBe('/super-admin?section=requests');
  });

  it('links an approved active Admin to the Admin dashboard',async()=>{
    await renderProfile(account('ADMIN'));
    const link=[...container.querySelectorAll('a')].find(x=>x.textContent.includes('Admin Dashboard'));
    expect(link?.getAttribute('href')).toBe('/admin?section=learners');
  });

  it.each([['LEARNER','ACTIVE'],['ADMIN','PENDING'],['ADMIN','REJECTED']])('hides administrative navigation for %s/%s',async(role,status)=>{
    await renderProfile(account(role,status));
    expect(container.querySelector('.roleDashboardLink')).toBeNull();
  });
});
