"""
>>==============================================================================<<
||  `.. ..    `..                                                               ||
||`..    `..  `..                                                               ||
|| `..      `.`. `.   `..    `. `...   `..       `..                            ||
||   `..      `..   `.   `..  `..    `.   `..  `..  `..                         ||
||      `..   `..  `..... `.. `..   `..... `..`..    `..                        ||
||`..    `..  `..  `.         `..   `.         `..  `..                         ||
||  `.. ..     `..   `....   `...     `....      `..                            ||
||                                                                              ||
||    `....                                                                     ||
||  `..    `..                                                                  ||
||`..        `..`. `..  `. `..  `. `...   `..     `....  `....    `..    `. `...||
||`..        `..`.  `.. `.  `..  `..    `.   `.. `..    `..     `..  `..  `..   ||
||`..        `..`.   `..`.   `.. `..   `..... `..  `...   `... `..    `.. `..   ||
||  `..     `.. `.. `.. `.. `..  `..   `.            `..    `.. `..  `..  `..   ||
||    `....     `..     `..     `...     `....   `.. `..`.. `..   `..    `...   ||
||              `..     `..                                                     ||
>>==============================================================================<<
"""

"""just a simple script to batch convert all STEREO .wavs in /stereo to MONO in /mono,
while retaining all SMPL chunk data, file names, and other important metadata.  
easier than loading everything into reaper and having to deal with all that. 
i needed it, 
hopefully you find it useful too  --conrad"""

import os
import struct
import numpy as np
import wave

def read_wav_file(file_path):
    with wave.open(file_path, 'rb') as wav_file:
        params = wav_file.getparams()
        frames = wav_file.readframes(params.nframes)
    
    chunks = []
    with open(file_path, 'rb') as file:
        file.seek(12)  # Skip RIFF header
        while True:
            try:
                chunk_id = file.read(4)
                if not chunk_id:
                    break
                chunk_size = struct.unpack('<I', file.read(4))[0]
                chunk_data = file.read(chunk_size)
                chunks.append((chunk_id, chunk_size, chunk_data))
                if chunk_size % 2:
                    file.read(1)  # Skip pad byte
            except struct.error:
                break
    
    return params, frames, chunks

def write_wav_file(file_path, params, frames, chunks):
    with wave.open(file_path, 'wb') as wav_file:
        wav_file.setparams(params)
        wav_file.writeframes(frames)
    
    with open(file_path, 'r+b') as file:
        file.seek(0, 2)  # Go to the end of the file
        for chunk in chunks:
            if chunk[0] not in [b'RIFF', b'fmt ', b'data']:
                file.write(chunk[0])
                file.write(struct.pack('<I', chunk[1]))  # Use original chunk size
                file.write(chunk[2])
                if chunk[1] % 2:
                    file.write(b'\x00')  # Pad byte
        
        # Update RIFF chunk size
        file_size = file.tell()
        file.seek(4, 0)
        file.write(struct.pack('<I', file_size - 8))

def convert_to_mono(stereo_frames, sample_width):
    dtype = f'int{sample_width*8}'
    samples = np.frombuffer(stereo_frames, dtype=dtype)
    stereo_samples = samples.reshape(-1, 2)
    mono_samples = np.mean(stereo_samples, axis=1, dtype=np.float32)
    return mono_samples.astype(dtype).tobytes()

def process_wav_file(input_file, output_file):
    params, frames, chunks = read_wav_file(input_file)
    
    if params.nchannels != 2:
        print(f"Skipping {input_file}: Not a stereo file")
        return
    
    mono_frames = convert_to_mono(frames, params.sampwidth)
    
    mono_params = params._replace(nchannels=1, 
                                  nframes=len(mono_frames) // params.sampwidth,
                                  comptype='NONE', 
                                  compname='not compressed')
    
    write_wav_file(output_file, mono_params, mono_frames, chunks)

def process_folder(input_folder, output_folder):
    for filename in os.listdir(input_folder):
        if filename.endswith(".wav"):
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, filename)
            
            try:
                process_wav_file(input_path, output_path)
                print(f"Converted {filename} to mono")
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")

if __name__ == "__main__":
    project_dir = os.getcwd()
    input_folder = os.path.join(project_dir, "stereo")
    output_folder = os.path.join(project_dir, "mono")
    
    if not os.path.exists(input_folder):
        print(f"Error: Input folder 'stereo' does not exist in {project_dir}")
        exit(1)
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    process_folder(input_folder, output_folder)
    print(f"Processing complete. Mono files are in: {output_folder}")