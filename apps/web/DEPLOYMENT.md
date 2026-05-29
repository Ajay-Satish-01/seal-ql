# Deploying to Vercel

The Intelligence Connector documentation site (`apps/web`) is built with Next.js and is optimized for deployment on Vercel.

## Vercel GUI Deployment Steps

Since this is a monorepo structure, follow these steps to deploy the frontend correctly using the Vercel Dashboard:

1. **Import Project**
   - Log into [Vercel](https://vercel.com).
   - Click **Add New...** > **Project**.
   - Import the `intelligence_connector` GitHub repository.

2. **Configure Monorepo Settings**
   - In the "Configure Project" step, click on **Root Directory**.
   - Select `apps/web` as the root directory. Vercel will automatically detect that this is a Next.js project.

3. **Build Settings**
   - **Framework Preset**: Next.js (Auto-detected).
   - **Build Command**: `pnpm build` (Auto-detected).
   - **Output Directory**: `.next` (Auto-detected).
   - **Install Command**: `pnpm install` (Auto-detected).

4. **Environment Variables**
   - (Optional) Add any required frontend environment variables here.

5. **Deploy**
   - Click **Deploy**. Vercel will install the dependencies using `pnpm` and build the Next.js application.

Your site will be live with a `.vercel.app` domain, and you can map a custom domain to it from the project settings.
