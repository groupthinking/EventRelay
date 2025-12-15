import React, { useState, useRef, useEffect, useCallback } from 'react';
import { AutoProcessor, AutoModelForImageTextToText, RawImage } from '@huggingface/transformers';
import { Box, Card, CardContent, Typography, Button, CircularProgress, Alert, Chip } from '@mui/material';
import { PlayArrow, Stop, Refresh } from '@mui/icons-material';

interface VLMVideoAnalyzerProps {
  videoUrl: string;
  onAnalysisComplete?: (analysis: string) => void;
}

const MODEL_ID = "onnx-community/FastVLM-0.5B-ONNX";
const MAX_NEW_TOKENS = 256;

export const VLMVideoAnalyzer: React.FC<VLMVideoAnalyzerProps> = ({
  videoUrl,
  onAnalysisComplete
}) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [currentPrompt, setCurrentPrompt] = useState<string>(
    "Describe what you see in this video frame in detail"
  );

  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const processorRef = useRef<any>(null);
  const modelRef = useRef<any>(null);

  const loadModel = useCallback(async () => {
    if (isLoaded) return;

    setIsLoading(true);
    setError(null);

    try {
      console.log('Loading FastVLM processor...');
      processorRef.current = await AutoProcessor.from_pretrained(MODEL_ID);

      console.log('Loading FastVLM model...');
      modelRef.current = await AutoModelForImageTextToText.from_pretrained(MODEL_ID, {
        dtype: {
          embed_tokens: "fp16",
          vision_encoder: "q4",
          decoder_model_merged: "q4",
        },
        device: "webgpu",
      });

      setIsLoaded(true);
      console.log('FastVLM model loaded successfully');
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : String(e);
      setError(`Failed to load model: ${errorMessage}`);
      console.error('Model loading error:', e);
    } finally {
      setIsLoading(false);
    }
  }, [isLoaded]);

  const analyzeFrame = useCallback(async (video: HTMLVideoElement, prompt: string): Promise<string> => {
    if (!processorRef.current || !modelRef.current) {
      throw new Error("Model not loaded");
    }

    if (!canvasRef.current) {
      canvasRef.current = document.createElement("canvas");
    }
    const canvas = canvasRef.current;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    if (!ctx) throw new Error("Could not get canvas context");

    ctx.drawImage(video, 0, 0);

    const frame = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const rawImg = new RawImage(frame.data, frame.width, frame.height, 4);

    const messages = [
      {
        role: "system",
        content: "You are a helpful visual AI assistant analyzing YouTube video content. Provide detailed, accurate descriptions.",
      },
      { role: "user", content: `<image>${prompt}` },
    ];

    const prompt_text = processorRef.current.apply_chat_template(messages, {
      add_generation_prompt: true,
    });

    const inputs = await processorRef.current(rawImg, prompt_text, {
      add_special_tokens: false,
    });

    const outputs = await modelRef.current.generate({
      ...inputs,
      max_new_tokens: MAX_NEW_TOKENS,
      do_sample: false,
      repetition_penalty: 1.2,
    });

    const decoded = processorRef.current.batch_decode(
      outputs.slice(null, [inputs.input_ids.dims.at(-1), null]),
      {
        skip_special_tokens: true,
      }
    );

    return decoded[0].trim();
  }, []);

  const analyzeVideo = useCallback(async () => {
    if (!videoRef.current || !isLoaded) return;

    setIsAnalyzing(true);
    setError(null);

    try {
      const video = videoRef.current;

      // Seek to a frame in the middle of the video for analysis
      video.currentTime = video.duration * 0.5;

      // Wait for the video to seek
      await new Promise((resolve) => {
        const onSeeked = () => {
          video.removeEventListener('seeked', onSeeked);
          resolve(void 0);
        };
        video.addEventListener('seeked', onSeeked);
      });

      const result = await analyzeFrame(video, currentPrompt);
      setAnalysis(result);

      if (onAnalysisComplete) {
        onAnalysisComplete(result);
      }
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : String(e);
      setError(`Analysis failed: ${errorMessage}`);
      console.error('Analysis error:', e);
    } finally {
      setIsAnalyzing(false);
    }
  }, [isLoaded, currentPrompt, analyzeFrame, onAnalysisComplete]);

  useEffect(() => {
    if (videoUrl && videoRef.current) {
      videoRef.current.src = videoUrl;
    }
  }, [videoUrl]);

  return (
    <Card sx={{ maxWidth: 800, mx: 'auto', mt: 2 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          AI Video Frame Analysis
          <Chip
            label={isLoaded ? "Model Ready" : "Model Loading"}
            color={isLoaded ? "success" : "warning"}
            size="small"
            sx={{ ml: 1 }}
          />
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Box sx={{ mb: 2 }}>
          <video
            ref={videoRef}
            controls
            style={{ width: '100%', maxHeight: '300px' }}
            crossOrigin="anonymous"
          />
        </Box>

        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Analysis Prompt:
          </Typography>
          <textarea
            value={currentPrompt}
            onChange={(e) => setCurrentPrompt(e.target.value)}
            rows={2}
            style={{
              width: '100%',
              padding: '8px',
              border: '1px solid #ccc',
              borderRadius: '4px',
              fontFamily: 'inherit'
            }}
            placeholder="Enter analysis prompt..."
          />
        </Box>

        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
          <Button
            variant="contained"
            onClick={loadModel}
            disabled={isLoaded || isLoading}
            startIcon={isLoading ? <CircularProgress size={16} /> : null}
          >
            {isLoading ? 'Loading Model...' : isLoaded ? 'Model Ready' : 'Load AI Model'}
          </Button>

          <Button
            variant="contained"
            onClick={analyzeVideo}
            disabled={!isLoaded || isAnalyzing}
            startIcon={isAnalyzing ? <CircularProgress size={16} /> : <PlayArrow />}
          >
            {isAnalyzing ? 'Analyzing...' : 'Analyze Frame'}
          </Button>

          <Button
            variant="outlined"
            onClick={() => setAnalysis('')}
            startIcon={<Refresh />}
          >
            Clear
          </Button>
        </Box>

        {analysis && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="h6" gutterBottom>
              Analysis Result:
            </Typography>
            <Box sx={{
              p: 2,
              bgcolor: 'grey.50',
              borderRadius: 1,
              border: '1px solid',
              borderColor: 'grey.200'
            }}>
              <Typography variant="body1">
                {analysis}
              </Typography>
            </Box>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};
