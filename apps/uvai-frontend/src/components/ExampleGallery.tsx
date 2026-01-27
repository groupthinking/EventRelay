import './ExampleGallery.css';

interface ExampleVideo {
  id: string;
  title: string;
  thumbnail: string;
  duration: string;
  category: string;
}

interface ExampleGalleryProps {
  onSelect: (videoId: string) => void;
}

const EXAMPLE_VIDEOS: ExampleVideo[] = [
  {
    id: 'dQw4w9WgXcQ',
    title: 'Music Video Analysis',
    thumbnail: 'https://img.youtube.com/vi/dQw4w9WgXcQ/mqdefault.jpg',
    duration: '3:33',
    category: 'Music',
  },
  {
    id: 'jNQXAC9IVRw',
    title: 'Me at the zoo',
    thumbnail: 'https://img.youtube.com/vi/jNQXAC9IVRw/mqdefault.jpg',
    duration: '0:19',
    category: 'Historic',
  },
  {
    id: 'ZK-fq29ZXPI',
    title: 'Tech Tutorial Demo',
    thumbnail: 'https://img.youtube.com/vi/ZK-fq29ZXPI/mqdefault.jpg',
    duration: '12:45',
    category: 'Tech',
  },
  {
    id: 'aircAruvnKk',
    title: 'Google I/O Keynote',
    thumbnail: 'https://img.youtube.com/vi/aircAruvnKk/mqdefault.jpg',
    duration: '1:53:21',
    category: 'Conference',
  },
];

export default function ExampleGallery({ onSelect }: ExampleGalleryProps) {
  const handleSelect = (video: ExampleVideo) => {
    const url = `https://www.youtube.com/watch?v=${video.id}`;
    onSelect(url);
  };

  return (
    <div className="example-gallery">
      <h3 className="gallery-title">Try an Example</h3>
      <div className="gallery-grid">
        {EXAMPLE_VIDEOS.map((video) => (
          <button
            key={video.id}
            className="example-card"
            onClick={() => handleSelect(video)}
          >
            <div className="card-thumbnail">
              <img
                src={video.thumbnail}
                alt={video.title}
                loading="lazy"
              />
              <span className="card-duration">{video.duration}</span>
              <div className="card-overlay">
                <span className="play-icon">▶</span>
              </div>
            </div>
            <div className="card-info">
              <span className="card-title">{video.title}</span>
              <span className="card-category">{video.category}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
