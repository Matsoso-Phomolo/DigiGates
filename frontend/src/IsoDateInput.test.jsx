// @vitest-environment jsdom
import React,{act,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {afterEach,beforeEach,describe,expect,it} from 'vitest';
import IsoDateInput,{isoDateError} from './IsoDateInput.jsx';

describe('ISO Date of Birth input',()=>{
  let container;let root;
  beforeEach(()=>{globalThis.IS_REACT_ACT_ENVIRONMENT=true;container=document.createElement('div');document.body.appendChild(container);root=createRoot(container)});
  afterEach(()=>{act(()=>root.unmount());container.remove()});
  function Controlled({initial=''}){const [value,setValue]=useState(initial);return <label>Date of Birth<IsoDateInput value={value} max="2026-12-31" onChange={event=>setValue(event.target.value)}/></label>}

  it('always exposes a visible YYYY-MM-DD text format and preserves an existing date',()=>{
    act(()=>root.render(<Controlled initial="1995-06-01"/>));const input=container.querySelector('input');
    expect(input.type).toBe('text');expect(input.placeholder).toBe('YYYY-MM-DD');expect(input.value).toBe('1995-06-01');expect(container.textContent).toContain('Format: YYYY-MM-DD');
  });

  it.each([['2026-02-30',true],['2024-02-29',false],['2025-02-29',true],['06/01/1995',true],['',false]])('validates %s without timezone conversion',(value,invalid)=>{
    expect(Boolean(isoDateError(value,'2026-12-31'))).toBe(invalid);
  });

  it('sets native accessible validity feedback while retaining the entered value',async()=>{
    act(()=>root.render(<Controlled/>));const input=container.querySelector('input');
    await act(async()=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,'2026-02-30');input.dispatchEvent(new Event('input',{bubbles:true}));await Promise.resolve()});
    expect(input.value).toBe('2026-02-30');expect(input.validationMessage).toContain('valid calendar date');
  });
});
