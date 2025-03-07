import neo4j from "neo4j-driver";

const driver = neo4j.driver(
  process.env.NEO4J_URI,
  neo4j.auth.basic(process.env.NEO4J_USERNAME, process.env.NEO4J_PASSWORD),
  { disableLosslessIntegers: true }
);

const getNeo4jSession = () =>
  driver.session({ database: process.env.NEO4J_DATABASE });

export { getNeo4jSession };
