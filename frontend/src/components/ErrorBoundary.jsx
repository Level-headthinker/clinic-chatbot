import React from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error("UI crashed", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="crash-screen">
          <div className="crash-card">
            <div className="crash-icon">
              <AlertTriangle size={28} />
            </div>
            <h1>Something broke on this page</h1>
            <p>
              The rest of ClinicBot is still safe. Reload the page and try again.
            </p>
            <button
              className="btn btn-primary"
              onClick={() => window.location.reload()}
            >
              <RotateCcw size={16} />
              Reload
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
