const Background = () => {
  return (
    <div
      className="fixed inset-0 bg-cover bg-center bg-no-repeat blur-[128px] -z-30"
      style={{
        backgroundImage:
          "url('https://storage.googleapis.com/neo4j-se-jeff-davis/test-bg2.png')",
      }}
    >
      <div className="absolute inset-0 bg-white opacity-40 -z-20" />
    </div>
  );
};

export default Background;
