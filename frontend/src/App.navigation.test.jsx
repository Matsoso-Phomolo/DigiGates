// @vitest-environment jsdom
import React,{act} from 'react';
import {createRoot} from 'react-dom/client';
import {MemoryRouter} from 'react-router-dom';
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest';
import App from './App.jsx';

const account=role=>({user_id:1,full_name:'Verified User',email:'verified@example.com',role,approval_status:'ACTIVE',gender:null,date_of_birth:null,is_active:true,created_at:'2026-01-01T00:00:00',updated_at:'2026-01-01T00:00:00'});
const response=value=>Promise.resolve({ok:true,status:200,json:()=>Promise.resolve(value)});

describe('verified application session navigation',()=>{
  let container; let root;
  beforeEach(()=>{container=document.createElement('div');document.body.appendChild(container);root=createRoot(container)});
  afterEach(()=>{act(()=>root.unmount());container.remove();localStorage.clear();vi.restoreAllMocks()});

  async function renderWithBackendUser(user,cached=account('SUPER_ADMIN')){
    localStorage.setItem('dg_token','test-token');localStorage.setItem('dg_user',JSON.stringify(cached));
    global.fetch=vi.fn(()=>response(user));
    await act(async()=>{root.render(<MemoryRouter initialEntries={['/profile']}><App/></MemoryRouter>);await new Promise(resolve=>setTimeout(resolve,0))});
  }

  it('uses the backend profile rather than editable cached role data',async()=>{
    await renderWithBackendUser(account('LEARNER'));
    expect(container.querySelector('.roleDashboardLink')).toBeNull();
    expect(container.textContent).toContain('LEARNER');
  });

  it('removes privileged navigation when the verified user logs out',async()=>{
    await renderWithBackendUser(account('SUPER_ADMIN'));
    expect(container.querySelector('.roleDashboardLink')?.getAttribute('href')).toBe('/super-admin');
    const logout=container.querySelector('button[title="Sign out"]');
    await act(async()=>{logout.dispatchEvent(new MouseEvent('click',{bubbles:true}));await Promise.resolve()});
    expect(container.querySelector('.roleDashboardLink')).toBeNull();
    expect(localStorage.getItem('dg_token')).toBeNull();
  });
});
