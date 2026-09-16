import express from 'express';
import type { NextFunction, Request, Response } from 'express';

const app = express();
const port = 3000;

app.use((req: Request, _res: Response, next: NextFunction) => {
  console.log(`${new Date().toISOString()} ${req.method} ${req.url}`);
  next();
});

app.get('/', (_req: Request, res: Response) => {
  res.send('Welcome to the server!');
});

app.get('/api/time', (_req: Request, res: Response) => {
  res.json({ time: Date.now(), timeZone: 'UTC' });
});

app.get('/api/status', (_req: Request, res: Response) => {
  res.json({ status: 'OK', uptime: process.uptime() });
});

app.get('/api/info', (_req: Request, res: Response) => {
  res.json({ author: 'Mikhail', version: '1.0' });
});

app.get('/api/user/:id', (req: Request, res: Response) => {
  res.json({
    message: 'User information',
    userId: req.params.id,
  });
});

app.get('/api/users', (_req: Request, res: Response) => {
  res.json({
    users: ['User1', 'User2', 'User3', 'User4'],
  });
});

app.get('/api/roles', (_req: Request, res: Response) => {
  res.json({
    roles: ['Administrator', 'User', 'Designer'],
  });
});

app.get('/api/tasks', (_req: Request, res: Response) => {
  res.json({
    tasks: {
      main: 'Build a project',
      secondary: 'Fix errors',
      optional: 'Make no mistakes',
    },
  });
});

app.get('/api/projects', (_req: Request, res: Response) => {
  res.json({
    projects: {
      Eirvale: {
        id: 0,
        description: 'Gamified kanban',
      },
      Something: {
        id: 1,
        description: 'Something',
      },
    },
  });
});

app.get('/api/tasks/:id', (req: Request, res: Response) => {
  res.json({
    id: req.params.id,
    task: 'Task 1',
  });
});

app.use((_req: Request, res: Response) => {
  res.status(404).send('Not Found');
});

app.listen(port, () => {
  console.log(`Listening on port ${port}`);
  console.log(`Server URL: http://localhost:${port}`);
});
