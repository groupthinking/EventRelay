
export interface GuidingPrinciple {
  id: string;
  title: string;
  points: string[];
}

export interface LayerDefinition {
  id: string;
  title: string;
  subtitle?: string;
  points: string[];
  connectionTextAfter?: string;
}

export interface CrossCuttingConcern {
  id: string;
  title: string;
  points: string[];
}

export interface ImplementationPhase {
  id: string;
  title: string;
  details: string[];
}

export interface SuccessCriterion {
  id: string;
  title: string;
  points: string[];
}
