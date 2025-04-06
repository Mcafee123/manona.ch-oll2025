# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build/Lint/Test Commands
- Install dependencies: `npm install`
- Development server: `npm run serve`
- Build for production: `npm run build`
- Lint code: `npm run lint`
- No specific test commands found in the project

## Code Style Guidelines
- **TypeScript**: Strict typing enabled, use explicit types
- **Formatting**: Follow Vue 3 + TypeScript conventions
- **Imports**: Use `@/` path alias for src directory imports
- **Components**: Vue 3 Single File Components (.vue)
- **Naming**: 
  - PascalCase for components
  - camelCase for variables and functions
  - kebab-case for filenames
- **Error Handling**: Log errors appropriately (console in dev, suppress in prod)
- **Linting**: Follows Vue3-essential, ESLint recommended, Vue/TypeScript rules
- **Module System**: ES modules (import/export)