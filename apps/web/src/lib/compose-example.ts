import { readFileSync } from 'fs';
import path from 'path';

export function getComposeExample(): string {
  const filePath = path.join(process.cwd(), 'public', 'compose', 'docker-compose.example.yml');
  return readFileSync(filePath, 'utf-8');
}
