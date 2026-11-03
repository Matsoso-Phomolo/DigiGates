import React,{useId} from 'react';

export const DISPLAY_DATE_PLACEHOLDER='YYYY/MM/DD';
export const todayApiDate=()=>{
  const now=new Date();
  return `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;
};
export const dateForDisplay=value=>value?value.replaceAll('-','/'):'';
export const dateForApi=value=>value?value.replaceAll('/','-'):null;

export function displayDateError(value,max=todayApiDate()){
  if(!value)return '';
  const match=/^(\d{4})\/(\d{2})\/(\d{2})$/.exec(value);
  if(!match)return 'Enter the date in YYYY/MM/DD format.';
  const year=Number(match[1]),month=Number(match[2]),day=Number(match[3]);
  if(month<1||month>12||day<1||day>new Date(Date.UTC(year,month,0)).getUTCDate())return 'Enter a valid calendar date in YYYY/MM/DD format.';
  if(max&&dateForApi(value)>max)return `Date must be ${dateForDisplay(max)} or earlier.`;
  return '';
}

export default function IsoDateInput({value,onChange,max=todayApiDate(),id,...props}){
  const generatedId=useId(),inputId=id||generatedId,helpId=`${inputId}-format`;
  const validate=event=>event.currentTarget.setCustomValidity(displayDateError(event.currentTarget.value,max));
  return <><input {...props} id={inputId} type="text" inputMode="numeric" autoComplete="bday" placeholder={DISPLAY_DATE_PLACEHOLDER} maxLength="10" pattern="\d{4}/\d{2}/\d{2}" aria-describedby={helpId} value={value} onChange={event=>{validate(event);onChange(event)}} onBlur={validate}/><small id={helpId}>Format: {DISPLAY_DATE_PLACEHOLDER}</small></>;
}
