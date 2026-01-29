import './ExampleGallery.css';

interface ExampleVideo {
  id: string;
  url: string;
  title: string;
  thumbnail: string;
}

interface ExampleGalleryProps {
  examples: ExampleVideo[];
  onSelect: (url: string) => void;
}

export default function ExampleGallery({ examples, onSelect }: ExampleGalleryProps) {
  return (
    <div className="example-gallery">
      <h3 className="gallery-title">Try an Example</h3>
      <div className="gallery-grid">
        {examples.map((video) => (
          <button
            key={video.id}
            className="example-card"
            onClick={() => onSelect(video.url)}
          >
            <div className="card-thumbnail">
              <img
                src={video.thumbnail}
                alt={video.title}
                loading="lazy"
              />
              <div className="card-overlay">
                <span className="play-icon">▶</span>
              </div>
            </div>
            <div className="card-info">
              <span className="card-title">{video.title}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
