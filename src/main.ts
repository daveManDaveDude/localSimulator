import './style.css';
import { createApp } from './app/createApp';

const mount = document.querySelector<HTMLElement>('#app');

if (!mount) {
  throw new Error('The application mount element #app was not found.');
}

const app = createApp(mount);

if (import.meta.hot) {
  import.meta.hot.dispose(app.dispose);
}
