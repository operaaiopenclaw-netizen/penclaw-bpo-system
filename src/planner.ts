export class Planner {
 buildPlan(agentNames: string[]) {
   return agentNames.map((agentName, index) => ({
     stepOrder: index + 1,
     agentName,
     actionType: "execute_agent"
   }));
 }
}
