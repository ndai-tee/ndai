from moviepy.editor import VideoFileClip, clips_array, vfx
import os

def process_videos(lip_sync_folder, minecraft_video_path):
    # Create output directory if it doesn't exist
    output_dir = "minecraft_output"
    os.makedirs(output_dir, exist_ok=True)

    # Load the minecraft video
    minecraft_clip = VideoFileClip(minecraft_video_path)
    
    # Calculate dimensions for square videos in vertical format
    target_size = 1080  # Square size for both videos
    
    # Resize and crop minecraft video to be square
    minecraft_resized = minecraft_clip.resize(height=target_size)
    # Crop from center to make it square
    x1 = (minecraft_resized.w - target_size) // 2
    minecraft_resized = minecraft_resized.crop(x1=x1, 
                                             x2=x1 + target_size,
                                             y1=0,
                                             y2=target_size)
    
    # Process each lip sync video in the folder
    for lip_sync_file in os.listdir(lip_sync_folder):
        if lip_sync_file.endswith(('.mp4', '.mov', '.avi')):
            # Load lip sync video
            lip_sync_path = os.path.join(lip_sync_folder, lip_sync_file)
            lip_sync_clip = VideoFileClip(lip_sync_path)
            
            # Resize and crop lip sync video to be square
            lip_sync_resized = lip_sync_clip.resize(height=target_size)
            # Crop from center to make it square
            x1 = (lip_sync_resized.w - target_size) // 2
            lip_sync_resized = lip_sync_resized.crop(x1=x1,
                                                    x2=x1 + target_size,
                                                    y1=0,
                                                    y2=target_size)
            
            # Create final composition with square videos stacked vertically
            final_clip = clips_array([[lip_sync_resized],
                                    [minecraft_resized.subclip(0, lip_sync_clip.duration)]])
            
            # Write output file to minecraft_output directory
            output_filename = os.path.join(output_dir, f"combined_{os.path.splitext(lip_sync_file)[0]}.mp4")
            final_clip.write_videofile(output_filename, 
                                     codec='libx264', 
                                     audio_codec='aac',
                                     fps=30)
            
            # Close clips to free up memory
            lip_sync_clip.close()
            
    # Close minecraft clip
    minecraft_clip.close()

if __name__ == "__main__":
    lip_sync_folder = "lip_sync_output"  # Folder containing lip sync videos
    minecraft_video = "minecraft_video.mp4"  # Minecraft video path
    
    if not os.path.exists(lip_sync_folder):
        print(f"Error: {lip_sync_folder} directory not found")
    elif not os.path.exists(minecraft_video):
        print(f"Error: {minecraft_video} not found")
    else:
        process_videos(lip_sync_folder, minecraft_video)
        print("Video processing complete!")
