import React from "react";
import { useParams } from "react-router-dom";
import PromptCardManager from "./PromptCardManager";

const AdminView = ({ projectId, projectName }) => {
  return (
    <div className="h-full bg-white dark:bg-dark-primary transition-colors duration-300">
      <PromptCardManager projectId={projectId} projectName={projectName} />
    </div>
  );
};

export default AdminView;
