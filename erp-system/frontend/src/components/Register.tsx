import { FormEvent, useState } from 'react';
import { authAPI } from '../services/api';
import '../styles/auth.css';

interface RegisterProps {
  onAuthenticated: () => void;
  onBack: () => void;
  language?: 'ar' | 'en';
}

export default function Register({ onAuthenticated, onBack, language = 'ar' }: RegisterProps) {
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const ar = language === 'ar';

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    setMessage('');
    setLoading(true);
    try {
      const response = await authAPI.register({
        email: email.trim(),
        password,
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        company_name: companyName.trim(),
      });
      const data = response.data?.data;
      if (data?.access_token && data?.user?.tenant_id) {
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token || '');
        localStorage.setItem('eos_tenant_id', String(data.user.tenant_id));
        localStorage.setItem('eos_user', JSON.stringify(data.user));
        onAuthenticated();
        return;
      }
      if (data?.verification_token && data?.user_id) {
        await authAPI.verifyEmail(data.verification_token);
        const login = await authAPI.login(email.trim(), password);
        const loginData = login.data?.data;
        if (loginData?.access_token && loginData?.user?.tenant_id) {
          localStorage.setItem('access_token', loginData.access_token);
          localStorage.setItem('refresh_token', loginData.refresh_token || '');
          localStorage.setItem('eos_tenant_id', String(loginData.user.tenant_id));
          localStorage.setItem('eos_user', JSON.stringify(loginData.user));
          onAuthenticated();
          return;
        }
      }
      setMessage(ar ? 'تم إنشاء الحساب. تحقق من بريدك الإلكتروني ثم سجّل الدخول.' : 'Account created. Verify your email, then sign in.');
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(String(detail?.error?.message || detail || (ar ? 'تعذر إنشاء الحساب' : 'Unable to create the account')));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="eos-login" dir={ar ? 'rtl' : 'ltr'}>
      <section className="eos-login-card" aria-labelledby="register-title">
        <div className="eos-brand eos-login-brand"><span className="eos-logo">E</span><span>EOS</span></div>
        <span className="eos-eyebrow">EOS DBP</span>
        <h1 id="register-title">{ar ? 'إنشاء حساب الشركة' : 'Create your company account'}</h1>
        <p>{ar ? 'ابدأ مساحة عمل ERP آمنة لشركتك.' : 'Start a secure ERP workspace for your company.'}</p>
        <form onSubmit={submit} noValidate>
          <div className="eos-auth-row">
            <label><span>{ar ? 'الاسم الأول' : 'First name'}</span><input required autoComplete="given-name" value={firstName} onChange={(e) => setFirstName(e.target.value)} disabled={loading} /></label>
            <label><span>{ar ? 'اسم العائلة' : 'Last name'}</span><input required autoComplete="family-name" value={lastName} onChange={(e) => setLastName(e.target.value)} disabled={loading} /></label>
          </div>
          <label><span>{ar ? 'اسم الشركة' : 'Company name'}</span><input required autoComplete="organization" value={companyName} onChange={(e) => setCompanyName(e.target.value)} disabled={loading} /></label>
          <label><span>{ar ? 'البريد الإلكتروني' : 'Email'}</span><input type="email" required autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} disabled={loading} /></label>
          <label><span>{ar ? 'كلمة المرور' : 'Password'}</span><input type="password" required minLength={10} autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} disabled={loading} /></label>
          {error && <div className="eos-login-error" role="alert">{error}</div>}
          {message && <div className="eos-login-success" role="status">{message}</div>}
          <button className="eos-primary-button eos-login-submit" type="submit" disabled={loading}>
            {loading ? (ar ? 'جارٍ إنشاء الحساب…' : 'Creating account…') : (ar ? 'إنشاء الحساب' : 'Create account')}
          </button>
          <button className="eos-ghost-button" type="button" onClick={onBack} disabled={loading}>{ar ? 'لدي حساب بالفعل' : 'I already have an account'}</button>
        </form>
      </section>
    </main>
  );
}
