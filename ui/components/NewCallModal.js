const NewCallModal = ({ handleClose }) => {
  return (
    <div className="modal modal-open">
      <div className="modal-box w-1/2 h-1/2 flex justify-center items-center">
        <button
          className="btn btn-xl bg-blue-700 text-white rounded-full"
          onClick={handleClose}
        >
          New Call
        </button>
      </div>
    </div>
  );
};

export default NewCallModal;
