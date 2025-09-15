import React from "react";

const ProgressBar = ({ current, total }) => {
  const percent = total > 0 ? Math.round((current / total) * 100) : 0;
  return (
    <div className="progress-wrapper">
      <div className="progress" role="progressbar" aria-valuenow={percent} aria-valuemin="0" aria-valuemax="100">
        <div className="progress-bar" style={{ width: `${percent}%` }}></div>
      </div>
      <div className="progress-label">{current}/{total} answered</div>
    </div>
  );
};

export default ProgressBar;
