// @vitest-environment jsdom
import React,{act} from 'react';
import {createRoot} from 'react-dom/client';
import {MemoryRouter} from 'react-router-dom';
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest';
import {AdminPortal,ProfileV2,SuperAdminPortal} from './AccountManagement.jsx';

const page={items:[],page:1,page_size:10,total:0,pages:1};
const ok=value=>Promise.resolve({ok:true,status:200,json:()=>Promise.resolve(value)});
const noContent=()=>Promise.resolve({ok:true,status:204,json:()=>Promise.resolve(null)});
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

describe('Administrator learner lifecycle actions',()=>{
  let container; let root;
  const learner=(id,name,email,is_active)=>({user_id:id,full_name:name,email,role:'LEARNER',approval_status:'ACTIVE',gender:null,date_of_birth:null,is_active,created_at:'2026-01-01T00:00:00',updated_at:'2026-01-01T00:00:00'});
  beforeEach(()=>{globalThis.IS_REACT_ACT_ENVIRONMENT=true;localStorage.setItem('dg_token','test-token');container=document.createElement('div');document.body.appendChild(container);root=createRoot(container);vi.spyOn(window,'confirm').mockReturnValue(true)});
  afterEach(()=>{act(()=>root.unmount());container.remove();localStorage.clear();vi.restoreAllMocks()});

  it('shows state-appropriate actions, refreshes, and requires DELETE confirmation',async()=>{
    let items=[learner(10,'Active Learner','active@example.com',true),learner(11,'Inactive Learner','inactive@example.com',false)];
    global.fetch=vi.fn((url,options={})=>{
      const path=String(url),method=options.method||'GET';
      if(method==='POST'&&path.endsWith('/10/deactivate')){items=items.map(x=>x.user_id===10?{...x,is_active:false}:x);return noContent()}
      if(method==='POST'&&path.endsWith('/11/reactivate')){items=items.map(x=>x.user_id===11?{...x,is_active:true}:x);return noContent()}
      if(method==='DELETE'&&path.endsWith('/10')){items=items.filter(x=>x.user_id!==10);return noContent()}
      return ok({...page,items,total:items.length});
    });
    await act(async()=>{root.render(<MemoryRouter initialEntries={['/admin?section=learners']}><AdminPortal/></MemoryRouter>);await Promise.resolve()});
    const row=email=>[...container.querySelectorAll('tbody tr')].find(x=>x.children[1]?.textContent===email);
    expect(row('active@example.com').textContent).toContain('Deactivate');
    expect(row('active@example.com').textContent).not.toContain('Reactivate');
    expect(row('inactive@example.com').textContent).toContain('Reactivate');
    expect(row('inactive@example.com').textContent).not.toContain('Deactivate');

    await click([...row('inactive@example.com').querySelectorAll('button')].find(x=>x.textContent==='Edit'));
    expect(container.querySelector('.managedForm input[type="email"]').value).toBe('inactive@example.com');
    await click([...container.querySelectorAll('.managedForm button')].find(x=>x.textContent==='Cancel'));

    await click([...row('active@example.com').querySelectorAll('button')].find(x=>x.textContent==='Deactivate'));
    expect(row('active@example.com').textContent).toContain('Reactivate');
    await click([...row('inactive@example.com').querySelectorAll('button')].find(x=>x.textContent==='Reactivate'));
    expect(row('inactive@example.com').textContent).toContain('Deactivate');

    await click([...row('active@example.com').querySelectorAll('button')].find(x=>x.textContent==='Delete'));
    const dialog=container.querySelector('[role="dialog"]');
    expect(dialog.textContent).toContain('Active Learner');
    expect(dialog.textContent).toContain('active@example.com');
    expect(dialog.textContent).toContain('This action permanently deletes the account and its associated user-owned data. It cannot be undone.');
    const confirmInput=dialog.querySelector('input');
    await act(async()=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(confirmInput,'DELETE');confirmInput.dispatchEvent(new Event('input',{bubbles:true}));await Promise.resolve()});
    const deleteButton=[...dialog.querySelectorAll('button')].find(x=>x.textContent==='Permanently Delete');
    expect(deleteButton.disabled).toBe(false);
    await click(deleteButton);
    expect(row('active@example.com')).toBeUndefined();
    expect(fetch.mock.calls.some(([url,options])=>String(url).endsWith('/admin/learners/10')&&options.method==='DELETE')).toBe(true);
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
