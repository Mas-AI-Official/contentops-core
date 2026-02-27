export default function VideoPlayer({ src, poster, className = '' }) {
  return (
    <div className={`video-container bg-black rounded-lg overflow-hidden ${className}`}>
      <video
        src={src}
        poster={poster}
        controls
        className="w-full h-full object-contain"
      >
        Your browser does not support the video tag.
      </video>
    </div>
  )
}
