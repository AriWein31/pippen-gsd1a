import React from 'react';
import { Card, CardContent } from './Card';
import { AlertIcon } from './Icons';
import { Button } from './Button';

interface ErrorBoundaryState {
  hasError: boolean;
}

export class ErrorBoundary extends React.Component<React.PropsWithChildren, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error): void {
    console.error('Pippen UI crashed', error);
  }

  handleReload = (): void => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#F6F7F9] px-4 py-8">
          <Card variant="outlined">
            <CardContent className="py-10 text-center space-y-4">
              <div className="mx-auto h-14 w-14 rounded-full bg-[#FEE2E2] flex items-center justify-center">
                <AlertIcon size={28} color="#DC2626" />
              </div>
              <div>
                <h1 className="text-xl font-semibold text-[#1A1D21]">Something went wrong</h1>
                <p className="text-sm text-[#8A8E97] mt-1">The app hit an unexpected error. Your saved data is still on this device.</p>
              </div>
              <Button onClick={this.handleReload}>Reload app</Button>
            </CardContent>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}
