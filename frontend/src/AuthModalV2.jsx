import React,{useEffect,useRef,useState} from 'react';
import {Link} from 'react-router-dom';
import {api} from './api.js';
import IsoDateInput,{isoDateError} from './IsoDateInput.jsx';

const genders=[['MALE','Male'],['FEMALE','Female'],['NON_BINARY','Non-binary'],['PREFER_NOT_TO_SAY','Prefer not to say']];

function AuthLogo(){return <Link className="logo" to="/"><span>▷</span><b>Digi<i>Gates</i></b><small>Understand Logic. Build Intelligence.</small></Link>}

export default function AuthModalV2({mode,setMode,close,onAuth}){
  const [form,setForm]=useState({full_name:'',email:'',password:'',requested_role:'LEARNER',gender:'',date_of_birth:''});
  const [error,setError]=useState(''),[notice,setNotice]=useState(''),[showPassword,setShowPassword]=useState(false);
  const dialogRef=useRef(null);
  useEffect(()=>{
    const previousFocus=document.activeElement,previousOverflow=document.body.style.overflow,dialog=dialogRef.current;
    document.body.style.overflow='hidden';dialog?.querySelector('input,select')?.focus();
    function keydown(event){
      if(event.key==='Escape'){event.preventDefault();close();return}
      if(event.key!=='Tab'||!dialog)return;
      const controls=[...dialog.querySelectorAll('button:not([disabled]),input:not([disabled]),select:not([disabled]),a[href]')];
      if(!controls.length)return;const first=controls[0],last=controls[controls.length-1];
      if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus()}
      else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus()}
    }
    document.addEventListener('keydown',keydown);
    return()=>{document.removeEventListener('keydown',keydown);document.body.style.overflow=previousOverflow;if(previousFocus instanceof HTMLElement&&previousFocus.isConnected)previousFocus.focus()};
  },[close]);
  async function submit(event){
    event.preventDefault();setError('');
    if(mode==='register'){const dateError=isoDateError(form.date_of_birth);if(dateError){setError(dateError);return}}
    try{
      const payload=mode==='login'?{email:form.email,password:form.password}:{...form,gender:form.gender||null,date_of_birth:form.date_of_birth||null};
      const data=await api(`/auth/${mode}`,{method:'POST',body:JSON.stringify(payload)});
      if(!data.access_token){setNotice(data.message);return}
      localStorage.setItem('dg_token',data.access_token);onAuth(data.user);
    }catch(submitError){setError(submitError.message)}
  }
  return <div className="modal"><section className="authDialog" ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby="auth-dialog-title"><button type="button" className="close" onClick={close} aria-label="Close authentication dialog">×</button><form onSubmit={submit}><AuthLogo/><h2 id="auth-dialog-title">{mode==='login'?'Welcome back':'Create account'}</h2>{mode==='register'&&<><label>Full Name<input required value={form.full_name} onChange={event=>setForm({...form,full_name:event.target.value})}/></label><label>Account type<select value={form.requested_role} onChange={event=>setForm({...form,requested_role:event.target.value})}><option value="LEARNER">Learner</option><option value="ADMIN">Administrator</option></select></label>{form.requested_role==='ADMIN'&&<p className="fieldHint">Administrator access remains pending until a Super Admin approves the request.</p>}<label>Gender<select value={form.gender} onChange={event=>setForm({...form,gender:event.target.value})}><option value="">Not provided</option>{genders.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label><label>Date of Birth<IsoDateInput value={form.date_of_birth} onChange={event=>setForm({...form,date_of_birth:event.target.value})}/></label></>}<label>Email Address<input type="email" required value={form.email} onChange={event=>setForm({...form,email:event.target.value})}/></label><label>Password<div className="password-field"><input type={showPassword?'text':'password'} minLength="8" required value={form.password} onChange={event=>setForm({...form,password:event.target.value})}/><button type="button" className="password-toggle" onClick={()=>setShowPassword(value=>!value)} aria-label={showPassword?'Hide password':'Show password'} title={showPassword?'Hide password':'Show password'}><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg></button></div></label>{notice&&<p className="profileNotice successNotice" role="status">{notice}</p>}{error&&<p className="error" role="alert">{error}</p>}<button className="primary">{mode==='login'?'Sign In':'Submit Registration'}</button><button type="button" className="link" onClick={()=>setMode(mode==='login'?'register':'login')}>{mode==='login'?<>Need an account? <span>Sign up</span></>:<>Already registered? <span>Sign in</span></>}</button></form></section></div>;
}
