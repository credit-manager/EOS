import { FormEvent, useState } from 'react';
import { authAPI } from '../services/api';
import '../styles/auth.css';

interface LoginProps {
  onAuthenticated: () => void;
  language?: 'ar' | 'en';
}

export default function Login({ onAuthenticated, language = 'ar' }: LoginProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const ar = language === 'ar';

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    setLoading(true);
    try {
      const response = await authAPI.login(email.trim(), password);
      const data = response.data?.data;
      const token = data?.access_token;
      const user = data?.user;
      if (!token || !user?.tenant_id) throw new Error('Invalid authentication response');
      localStorage.setItem('access_token', token);
      localStorage.setItem('eos_tenant_id', String(user.tenant_id));
      localStorage.setItem('eos_user', JSON.stringify(user));
      onAuthenticated();
    } catch (err: any) {
      const message = err?.response?.data?.detail?.error?.message
        || err?.response?.data?.detail
        || (ar ? 'بيانات الدخول غير صحيحة' : 'Invalid email or password');
      setError(String(message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="eos-login" dir={ar ? 'rtl' : 'ltr'}>
      <section className="eos-login-card" aria-labelledby="login-title">
        <div className="eos-brand eos-login-brand"><span className="eos-logo">E</span><span>EOS</span></div>
        <span className="eos-eyebrow">EOS DBP</span>
        <h1 id="login-title">{ar ? 'تسجيل الدخول' : 'Sign in'}</h1>
        <p>{ar ? 'ادخل إلى مساحة عمل شركتك الآمنة.' : 'Access your secure company workspace.'}</p>
        <form onSubmit={submit} noValidate>
          <label>
            <span>{ar ? 'البريد الإلكتروني' : 'Email'}</span>
            <input type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} disabled={loading} />
          </label>
          <label>
            <span>{ar ? 'كلمة المرور' : 'Password'}</span>
            <input type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} disabled={loading} />
          </label>
          {error && <div className="eos-login-error" role="alert">{error}</div>}
          <button className="eos-primary-button eos-login-submit" type="submit" disabled={loading}>
            {loading ? (ar ? 'جارٍ الدخول…' : 'Signing in…') : (ar ? 'دخول' : 'Sign in')}
          </button>
        </form>
      </section>
    </main>
  );
}
